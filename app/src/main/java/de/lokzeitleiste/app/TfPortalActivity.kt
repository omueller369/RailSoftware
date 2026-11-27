/* Der WebView nutzt die gemeinsamen Portaldateien; die nativen Brücken übernehmen GPS, Downloads und lokale Dateien. */
package de.lokzeitleiste.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.*
import android.webkit.*
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import androidx.webkit.JavaScriptReplyProxy
import de.lokzeitleiste.app.network.*
import de.lokzeitleiste.app.portal.*
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

class TfPortalActivity : ComponentActivity() {
    private var helpPrintView: WebView?=null
    private lateinit var web: WebView
    private lateinit var policy: PortalPolicy
    private lateinit var store: GpsTrackStore
    private lateinit var updater:PortalUpdater
    private var session=JSONObject()
    private var fileCallback: ValueCallback<Array<Uri>>?=null
    private var pendingGps: Pair<JSONObject,JavaScriptReplyProxy>?=null
    private var pendingDownload: String?=null
    private var pendingExport: Pair<String,JavaScriptReplyProxy>?=null
    private var exportStream: OutputStream?=null
    private var exportId: String?=null
    private var exportBytes=0L
    private var leaving=false
    private var networkCallback:android.net.ConnectivityManager.NetworkCallback?=null
    private var identityRefresh:Job?=null
    private fun connected():Boolean=runCatching {
        val manager=getSystemService(android.net.ConnectivityManager::class.java)
        val capabilities=manager.getNetworkCapabilities(manager.activeNetwork)
        capabilities?.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED)==true
    }.getOrDefault(false)
    private fun watchNetwork() {
        val manager=getSystemService(android.net.ConnectivityManager::class.java)
        val callback=object:android.net.ConnectivityManager.NetworkCallback(){
            override fun onCapabilitiesChanged(network:android.net.Network,capabilities:android.net.NetworkCapabilities){networkChanged()}
            override fun onLost(network:android.net.Network){networkChanged()}
        }
        networkCallback=callback;manager.registerDefaultNetworkCallback(callback)
    }
    private fun networkChanged(){runOnUiThread {
        if(leaving||!::web.isInitialized)return@runOnUiThread
        web.evaluateJavascript("window.AndroidPortal?.setOnline?.(${connected()})",null)
        if(connected()&&session.has("account"))refreshIdentity()
    }}
    private fun refreshIdentity(){
        if(identityRefresh?.isActive==true||leaving)return
        identityRefresh=lifecycleScope.launch {
            val token=TokenVault.token(this@TfPortalActivity)?:return@launch
            try{
                val account=ApiClient.identity(token)
                if(account.optString("role")!="tf"){logout(true);return@launch}
                if(account.optBoolean("password_change_required")){logout(true);return@launch}
                val profile=ApiClient.portalIdentity(token)
                require(profile.getInt("id")==session.getJSONObject("account").getInt("id"))
                session=JSONObject().put("account",account).put("profile",profile).put("username",TokenVault.username(this@TfPortalActivity))
                OfflineSession(this@TfPortalActivity,policy.origin,TokenVault.username(this@TfPortalActivity)).save(session)
            }catch(_:AuthenticationRequired){logout(true)}catch(error:ServerRejected){if(error.status in listOf(401,403))logout(true)}catch(_:Exception){/* Offline work remains local; no transport error invalidates the saved identity. */}
        }
    }
    private val filePicker=registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val callback=fileCallback;fileCallback=null
        val uris=runCatching { WebChromeClient.FileChooserParams.parseResult(result.resultCode,result.data)?.filter { it.scheme=="content" }?.toTypedArray() }.getOrNull()
        runCatching { callback?.onReceiveValue(uris?.takeIf { it.isNotEmpty() }) }
    }
    private val locationPermission=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        val job=pendingGps;pendingGps=null
        if(job!=null) if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED) startGps(job.first,job.second)
        else reply(job.second,job.first,false,"Präziser Standort wurde nicht erlaubt.")
    }
    private var saveMimeType = "application/octet-stream"
    private val saveFile=registerForActivityResult(object : ActivityResultContracts.CreateDocument("*/*") {
        override fun createIntent(context: Context, input: String): Intent = super.createIntent(context, input).setType(saveMimeType)
    }) { uri ->
        val export=pendingExport;pendingExport=null
        if(export!=null) {
            if(uri==null) reply(export.second,JSONObject().put("id",export.first),false,"Speichern abgebrochen.")
            else try { exportStream=contentResolver.openOutputStream(uri,"wt");require(exportStream!=null);exportId=UUID.randomUUID().toString();exportBytes=0;reply(export.second,JSONObject().put("id",export.first),true,JSONObject().put("export_id",exportId)) }
            catch(error:Exception) { reply(export.second,JSONObject().put("id",export.first),false,error.message?:"Datei konnte nicht gespeichert werden.") }
        } else {
            val url=pendingDownload;pendingDownload=null
            if(uri!=null && url!=null) download(url,uri)
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if(TokenVault.username(this).isBlank()) { login();return }
        try { policy=PortalPolicy(ApiClient.base()) } catch(error:Exception) { toast(error.message?:"Serveradresse (HTTPS) prüfen.");finish();return }
        store=GpsTrackStore(this)
        LanguageRuntime.initialize(this)
        LanguageRuntime.code=getSharedPreferences("lokzeitleiste_language",MODE_PRIVATE).getString("language","de")?:"de"
        web=WebView(this).apply { fitsSystemWindows=true };setContentView(web)
        updater=PortalUpdater(this,autoOffer=false)
        configureWebView()
        watchNetwork()
        onBackPressedDispatcher.addCallback(this,object:OnBackPressedCallback(true) { override fun handleOnBackPressed() {
            web.evaluateJavascript("Boolean(window.TrainWorkspace?.back?.())") { handled ->
                if(handled!="true") {
                    if(GpsRecordingService.currentKey!=null) toast("Bitte zuerst die GPS-Aufzeichnung beenden.")
                    else if(web.canGoBack())web.goBack() else finish()
                }
            }
        } })
        lifecycleScope.launch { initialize() }
    }
    private fun toast(message:String) {
        val notice=Toast.makeText(this,LanguageRuntime.translate(message,LanguageRuntime.code),Toast.LENGTH_LONG)
        notice.show()
        if(message.contains("GPS",ignoreCase=true) || message.contains("HTTPS",ignoreCase=true)) {
            Handler(Looper.getMainLooper()).postDelayed({ notice.cancel() },3000L)
        }
    }
    private fun login() { startActivity(Intent(this,MainActivity::class.java));finish() }
    private fun logout(force:Boolean=false) {
        if(GpsRecordingService.currentKey!=null) { if(!force){toast("Bitte zuerst die GPS-Aufzeichnung beenden.");return};stopService(Intent(this,GpsRecordingService::class.java));GpsRecordingService.currentKey=null }
        if(leaving)return;leaving=true
        if(force)toast(AuthenticationRequired().message.orEmpty())
        val token=TokenVault.token(this)
        lifecycleScope.launch {
            if(token!=null) runCatching { withTimeout(5000) { ApiClient.logout(token) } }
            TokenVault.clear(this@TfPortalActivity)
            CookieManager.getInstance().removeAllCookies { CookieManager.getInstance().flush();login() }
        }
    }
    private suspend fun initialize() {
        val token=TokenVault.token(this) ?: return login()
        val username=TokenVault.username(this)
        val saved=OfflineSession(this,policy.origin,username)
        val cached=saved.read()
        if(cached!=null){session=cached;openSession(token);if(connected())refreshIdentity();return}
        try {
            val account=ApiClient.identity(token)
            require(account.optString("role")=="tf") { "TF Portal ist nur für Triebfahrzeugführer verfügbar." }
            val profile=if(account.optBoolean("password_change_required")) JSONObject() else ApiClient.portalIdentity(token)
            session=JSONObject().put("account",account).put("profile",profile).put("username",username)
            saved.save(session);openSession(token)
        } catch(_:AuthenticationRequired) { logout(true) }
        catch(error:Exception) { toast(error.message?:"Server nicht erreichbar. Bitte zunächst online anmelden.");finish() }
    }
    private fun openSession(token:String) {
        val secure=if(policy.origin.startsWith("https:")) "; Secure" else ""
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setCookie(policy.origin,"tf_session=$token; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000$secure") {
            CookieManager.getInstance().flush()
            web.loadUrl(policy.origin+if(session.getJSONObject("account").optBoolean("password_change_required")) "/account" else if(GpsRecordingService.currentKey!=null) "/tf/arbeitsbericht" else "/tf")
        }
    }
    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        web.settings.apply { javaScriptEnabled=true;domStorageEnabled=true;allowFileAccess=false;allowContentAccess=true;mixedContentMode=WebSettings.MIXED_CONTENT_NEVER_ALLOW;setSupportMultipleWindows(false);javaScriptCanOpenWindowsAutomatically=false;setGeolocationEnabled(false);userAgentString += " LokZeitleisteAndroid/0.11" }
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        if(WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(web,"NativePortal",setOf(policy.origin)) { _,message,origin,isMainFrame,proxy ->
                if(isMainFrame && policy.sameOrigin(origin.toString()) && policy.sameOrigin(web.url.orEmpty())) {
                    try { require((message.data?.length?:0)<150000);handle(JSONObject(message.data?:"{}"),proxy) }
                    catch(error:Exception) { toast(error.message?:"App-Anfrage fehlgeschlagen.") }
                }
            }
        } else toast("Android System WebView aktualisieren, um GPS und GPX-Export zu verwenden.")
        web.webViewClient=object:WebViewClient() {
            override fun shouldOverrideUrlLoading(view:WebView,request:WebResourceRequest):Boolean {
                val value=request.url.toString()
                if(policy.sameOrigin(value)) {
                    if(GpsRecordingService.currentKey!=null && request.isForMainFrame) { toast("Bitte zuerst die GPS-Aufzeichnung beenden.");return true }
                    return false
                }
                if(request.isForMainFrame && request.hasGesture() && request.url.scheme in listOf("https","http","tel","mailto")) runCatching { startActivity(Intent(Intent.ACTION_VIEW,request.url)) }
                return true
            }
            override fun shouldInterceptRequest(view:WebView,request:WebResourceRequest):WebResourceResponse? {
                if(!request.isForMainFrame && request.method=="GET" && policy.mapTile(request.url.toString())) return null
                if(!policy.sameOrigin(request.url.toString())) return WebResourceResponse("text/plain","UTF-8",403,"Forbidden",emptyMap(),ByteArrayInputStream(byteArrayOf()))
                if(request.method!="GET")return null
                if(request.url.path=="/locales/catalog.json")return WebResourceResponse("application/json","UTF-8",assets.open("catalog.json"))
                val name=policy.asset(request.url.path.orEmpty()) ?: return null
                return try {
                    var bytes=assets.open("tf-portal/$name").use { it.readBytes() }
                    if(name.endsWith(".html")) bytes=String(bytes,Charsets.UTF_8).replace("<head>","<head><script src=\"/map-gestures.js\"></script><script src=\"/android-offline.js\"></script><script src=\"/android-portal.js\"></script>").toByteArray(Charsets.UTF_8)
                    val mime=when { name.endsWith(".html")->"text/html";name.endsWith(".json")->"application/json";name.endsWith(".css")->"text/css";name.endsWith(".png")->"image/png";name.endsWith(".wasm")->"application/wasm";name.endsWith(".bcmap")||name.endsWith(".pfb")||name.endsWith(".ttf")->"application/octet-stream";else->"text/javascript" }
                    WebResourceResponse(mime,"UTF-8",200,"OK",mapOf("Cache-Control" to "no-store","Content-Security-Policy" to (if(name=="tf-portal.html") "frame-src ${policy.origin}/tf/bremszettel ${policy.origin}/tf/arbeitsbericht; object-src 'none'" else "frame-src ${policy.origin}/tf/arbeitsbericht; object-src 'none'")),ByteArrayInputStream(bytes))
                } catch(_:Exception) { WebResourceResponse("text/plain","UTF-8",500,"Missing portal asset",emptyMap(),ByteArrayInputStream(byteArrayOf())) }
            }
            override fun onReceivedSslError(view:WebView,handler:SslErrorHandler,error:android.net.http.SslError) { handler.cancel();toast("Das HTTPS-Zertifikat des Servers ist ungültig.") }
        }
        web.webChromeClient=object:WebChromeClient() {
            override fun onJsAlert(view:WebView,url:String,message:String,result:JsResult):Boolean { android.app.AlertDialog.Builder(this@TfPortalActivity).setMessage(message).setPositiveButton(android.R.string.ok) { _,_->result.confirm() }.setOnCancelListener { result.cancel() }.show();return true }
            override fun onJsConfirm(view:WebView,url:String,message:String,result:JsResult):Boolean { android.app.AlertDialog.Builder(this@TfPortalActivity).setMessage(message).setPositiveButton(android.R.string.ok) { _,_->result.confirm() }.setNegativeButton(android.R.string.cancel) { _,_->result.cancel() }.setOnCancelListener { result.cancel() }.show();return true }
            override fun onShowFileChooser(view:WebView,callback:ValueCallback<Array<Uri>>,params:FileChooserParams):Boolean {
                val previous=fileCallback;fileCallback=null;runCatching { previous?.onReceiveValue(null) };fileCallback=callback
                val intent=Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*").putExtra(Intent.EXTRA_ALLOW_MULTIPLE,params.mode==FileChooserParams.MODE_OPEN_MULTIPLE)
                val types=params.acceptTypes.orEmpty().filter { it.contains('/') }.toTypedArray();if(types.isNotEmpty())intent.putExtra(Intent.EXTRA_MIME_TYPES,types)
                try { filePicker.launch(intent) } catch(_:Exception) { fileCallback=null;runCatching { callback.onReceiveValue(null) } }
                return true
            }
        }
        web.setDownloadListener { url,_,disposition,mime,_->
            if(policy.sameOrigin(url) && pendingDownload==null && pendingExport==null && exportStream==null) { val name=DownloadMetadata.name(disposition.orEmpty(),URLUtil.guessFileName(url,disposition,mime));saveMimeType=DownloadMetadata.mime(name,mime);pendingDownload=url;saveFile.launch(name) }
            else toast("Download kann nicht geöffnet werden.")
        }
    }
    private fun reply(proxy:JavaScriptReplyProxy,request:JSONObject,ok:Boolean,value:Any) {
        proxy.postMessage(JSONObject().put("id",request.optString("id")).put("ok",ok).put(if(ok)"value" else "error",value).toString())
    }
    private fun trackKey(request:JSONObject):String {
        val key=request.getString("key");require(key.startsWith(session.getJSONObject("profile").getInt("id").toString()+"."));require(key.matches(Regex("[0-9]+\\.[A-Za-z0-9-]{1,100}")));return key
    }
    private fun handle(request:JSONObject,proxy:JavaScriptReplyProxy) {
        try {
            when(request.getString("method")) {
                "help.print" -> startHelpPrint(request,proxy)
                "report.print" -> startHelpPrint(request,proxy,true)
                "traffic.status" -> reply(proxy,request,true,JSONObject().put("upload",android.net.TrafficStats.getUidTxBytes(android.os.Process.myUid())).put("download",android.net.TrafficStats.getUidRxBytes(android.os.Process.myUid())))
                "session" -> reply(proxy,request,true,JSONObject(session.toString()).put("app_version",BuildConfig.VERSION_NAME).put("online",connected()))
                "network.status" -> reply(proxy,request,true,JSONObject().put("online",connected()))
                "language" -> {
                    val language=request.getString("language");require(language in LanguageRuntime.codes);LanguageRuntime.code=language
                    getSharedPreferences("lokzeitleiste_language",MODE_PRIVATE).edit().putString("language",language).apply()
                    reply(proxy,request,true,JSONObject())
                }
                "screen.fullscreen" -> {
                    require(Uri.parse(web.url).path in listOf("/tf/arbeitsbericht","/tf/gps-demo"))
                    PortalScreenMode.apply(this,request.optBoolean("enabled"))
                    reply(proxy,request,true,JSONObject())
                }
                "external.db" -> {
                    require(Uri.parse(web.url).path=="/tf/arbeitsbericht")
                    DigiCommandBrowser.open(this)
                    reply(proxy,request,true,JSONObject())
                }
                "updates.status" -> reply(proxy,request,true,updater.status())
                "updates.check" -> {
                    require(Uri.parse(web.url).path=="/tf/updates")
                    updater.check(true);reply(proxy,request,true,updater.status())
                }
                "logout" -> { reply(proxy,request,true,JSONObject());logout() }
                "expired" -> { reply(proxy,request,true,JSONObject());logout(true) }
                "gps.start" -> {
                    require(Uri.parse(web.url).path=="/tf/arbeitsbericht")
                    trackKey(request)
                    if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED) {
                        require(pendingGps==null);pendingGps=request to proxy
                        val permissions=mutableListOf(Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION)
                        if(Build.VERSION.SDK_INT>=33) permissions.add(Manifest.permission.POST_NOTIFICATIONS)
                        locationPermission.launch(permissions.toTypedArray())
                    } else startGps(request,proxy)
                }
                "gps.archiveInfo" -> {
                    val key=trackKey(request)
                    if(GpsRecordingService.currentKey==key){
                        reply(proxy,request,true,JSONObject().put("running",true).put("count",0).put("last",0))
                    } else lifecycleScope.launch {
                        try {
                            val info=withContext(Dispatchers.IO){store.summary(key)}
                            info.put("running",GpsRecordingService.currentKey==key)
                            if(!leaving&&!isFinishing&&!isDestroyed)runCatching { reply(proxy,request,true,info) }
                        } catch(error:Exception) {
                            if(!leaving&&!isFinishing&&!isDestroyed)runCatching { reply(proxy,request,false,error.message?:"GPS archive unavailable") }
                        }
                    }
                }
                "gps.snapshot" -> {
                    val key=trackKey(request);val after=request.optLong("after",0);val points=store.read(key);val result=JSONArray()
                    for(i in 0 until points.length()) if(points.getJSONObject(i).getLong("t")>after && result.length()<1000)result.put(points.getJSONObject(i))
                    reply(proxy,request,true,GpsLiveShare.status(key).put("points",result).put("running",GpsRecordingService.currentKey==key).put("paused",GpsRecordingService.currentKey==key && GpsRecordingService.paused))
                }
                "gps.share" -> {
                    require(Uri.parse(web.url).path=="/tf/arbeitsbericht")
                    val key=trackKey(request)
                    if(request.optBoolean("enabled"))GpsLiveShare.configure(this,key,request.getString("session_id"),request.getString("train_number"),request.optJSONArray("manual_stops")?:JSONArray(),if(request.isNull("stop_minutes"))null else request.getInt("stop_minutes"))
                    else GpsLiveShare.stop(this,key)
                    reply(proxy,request,true,GpsLiveShare.status(key))
                }
                "gps.shareContext" -> {
                    val key=trackKey(request)
                    GpsLiveShare.context(key,request.getString("session_id"),request.getString("train_number"),request.optJSONArray("manual_stops")?:JSONArray())
                    reply(proxy,request,true,GpsLiveShare.status(key))
                }
                "gps.pause" -> {
                    require(Uri.parse(web.url).path=="/tf/arbeitsbericht")
                    val key=trackKey(request);require(GpsRecordingService.currentKey==key)
                    val paused=request.getBoolean("paused")
                    startService(Intent(this,GpsRecordingService::class.java).putExtra("key",key).putExtra("paused",paused))
                    lifecycleScope.launch {
                        try {
                            withTimeout(2000) { while(GpsRecordingService.currentKey==key && GpsRecordingService.paused!=paused) delay(10) }
                            require(GpsRecordingService.currentKey==key && GpsRecordingService.paused==paused)
                            reply(proxy,request,true,JSONObject().put("paused",paused))
                        } catch(_:Exception) { reply(proxy,request,false,"GPS konnte nicht gestartet werden.") }
                    }
                }
                "gps.stop" -> { val key=trackKey(request);if(GpsRecordingService.currentKey==key){stopService(Intent(this,GpsRecordingService::class.java));GpsRecordingService.currentKey=null};reply(proxy,request,true,JSONObject()) }
                "gps.erase" -> { val key=trackKey(request);require(GpsRecordingService.currentKey!=key);store.erase(key);reply(proxy,request,true,JSONObject()) }
                "export.start" -> {
                    require(pendingDownload==null && pendingExport==null && exportStream==null)
                    saveMimeType=DownloadMetadata.mime(request.optString("name"),null)
                    pendingExport=request.getString("id") to proxy
                    saveFile.launch(request.optString("name","Dokument").replace(Regex("[/\\\\\\x00-\\x1f]"),"_").take(180))
                }
                "export.chunk" -> {
                    require(request.getString("export_id")==exportId && exportStream!=null)
                    val bytes=android.util.Base64.decode(request.getString("data"),android.util.Base64.DEFAULT)
                    require(bytes.size<=65536 && exportBytes+bytes.size<=32*1024*1024);exportStream!!.write(bytes);exportBytes+=bytes.size;reply(proxy,request,true,JSONObject())
                }
                "export.finish" -> { require(request.getString("export_id")==exportId);exportStream?.close();exportStream=null;exportId=null;reply(proxy,request,true,JSONObject()) }
                else -> reply(proxy,request,false,"Unbekannte App-Anfrage.")
            }
        } catch(error:Exception) { reply(proxy,request,false,error.message?:"App-Anfrage fehlgeschlagen.") }
    }
    private fun startHelpPrint(request:JSONObject,proxy:JavaScriptReplyProxy,report:Boolean=false) {
        require(helpPrintView==null) { "Ein Druckvorgang läuft bereits." }
        val title=request.getString("title")
        val html=if(report)ReportPrintDocument.render(title,request.getString("text")) else HelpPrintDocument.render(title,request.getString("text"))
        val jobTitle=if(report)title else "Anleitung – $title"
        val printView=WebView(this);helpPrintView=printView
        printView.settings.apply { javaScriptEnabled=false;allowFileAccess=false;allowContentAccess=false;blockNetworkLoads=true }
        var started=false
        printView.webViewClient=object:WebViewClient() {
            override fun onPageFinished(view:WebView,url:String) {
                if(started)return;started=true
                view.post {
                    try {
                        val delegate=view.createPrintDocumentAdapter(jobTitle)
                        val adapter=object:PrintDocumentAdapter() {
                            override fun onStart() { delegate.onStart() }
                            override fun onLayout(old:PrintAttributes?,new:PrintAttributes?,signal:CancellationSignal,callback:LayoutResultCallback,extras:Bundle?) { delegate.onLayout(old,new,signal,callback,extras) }
                            override fun onWrite(pages:Array<PageRange>,destination:ParcelFileDescriptor,signal:CancellationSignal,callback:WriteResultCallback) { delegate.onWrite(pages,destination,signal,callback) }
                            override fun onFinish() { delegate.onFinish();runOnUiThread { if(helpPrintView===view)helpPrintView=null;view.destroy() } }
                        }
                        getSystemService(PrintManager::class.java).print(jobTitle,adapter,PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build())
                        reply(proxy,request,true,JSONObject())
                    } catch(error:Exception) { helpPrintView=null;view.destroy();reply(proxy,request,false,error.message?:"Druckdialog konnte nicht geöffnet werden.") }
                }
            }
        }
        printView.loadDataWithBaseURL(null,html,"text/html","UTF-8",null)
    }
    private fun startGps(request:JSONObject,proxy:JavaScriptReplyProxy) {
        try {
            val key=trackKey(request);require(GpsRecordingService.currentKey==null || GpsRecordingService.currentKey==key) { "Eine andere GPS-Aufzeichnung läuft bereits." }
            require(getSystemService(android.location.LocationManager::class.java).isProviderEnabled(android.location.LocationManager.GPS_PROVIDER)) { "GPS in den Android-Einstellungen einschalten." }
            if(GpsRecordingService.currentKey==null) { store.begin(key,request.optBoolean("reset"));GpsRecordingService.currentKey=key;startForegroundService(Intent(this,GpsRecordingService::class.java).putExtra("key",key)) }
            reply(proxy,request,true,JSONObject())
        } catch(error:Exception) { GpsRecordingService.currentKey=null;reply(proxy,request,false,error.message?:"GPS konnte nicht gestartet werden.") }
    }
    private fun download(url:String,destination:Uri) {
        val cookie=CookieManager.getInstance().getCookie(policy.origin)
        lifecycleScope.launch {
            try { val mime=withContext(Dispatchers.IO) {
                require(policy.sameOrigin(url));val connection=URL(url).openConnection() as HttpURLConnection
                try { connection.instanceFollowRedirects=false;connection.connectTimeout=15000;connection.readTimeout=30000;connection.setRequestProperty("Cookie",cookie.orEmpty());require(connection.responseCode in 200..299) { "Download fehlgeschlagen (${connection.responseCode})." }
                    contentResolver.openOutputStream(destination,"wt")!!.use { output->connection.inputStream.use { input->input.copyTo(output) } }
                    connection.contentType?.substringBefore(';')?:"application/octet-stream"
                } finally { connection.disconnect() }
            };android.app.AlertDialog.Builder(this@TfPortalActivity).setMessage(LanguageRuntime.translate("Dokument gespeichert.",LanguageRuntime.code)).setPositiveButton(LanguageRuntime.translate("Ansehen",LanguageRuntime.code)) { _,_->
                    runCatching { startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(destination,mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)) }.onFailure { toast("Keine passende App zum Öffnen vorhanden.") }
                }.setNegativeButton(android.R.string.cancel,null).show() } catch(error:Exception) { toast(error.message?:"Download fehlgeschlagen.") }
        }
    }
    override fun onResume() { super.onResume();if(::updater.isInitialized)updater.resume() }
    override fun onDestroy() { networkCallback?.let { runCatching { getSystemService(android.net.ConnectivityManager::class.java).unregisterNetworkCallback(it) } };networkCallback=null;identityRefresh?.cancel();helpPrintView?.destroy();helpPrintView=null;val callback=fileCallback;fileCallback=null;runCatching { callback?.onReceiveValue(null) };exportStream?.close();if(::web.isInitialized){web.stopLoading();web.destroy()};super.onDestroy() }
}
