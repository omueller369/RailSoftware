package de.lokzeitleiste.app.portal

import android.content.Context
import de.lokzeitleiste.app.network.ApiClient
import de.lokzeitleiste.app.network.TokenVault
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Session exists only after an explicit share action. No location backlog is uploaded. */
object GpsLiveShare {
    private data class State(val key:String,val session:String,var train:String,var manual:JSONArray,val stopMinutes:Int?,@Volatile var attempted:Long=0,@Volatile var sent:Long=0)
    private val executor=Executors.newSingleThreadExecutor()
    private val busy=AtomicBoolean(false)
    @Volatile private var state:State?=null
    @Synchronized fun configure(context:Context,key:String,session:String,train:String,manual:JSONArray,stopMinutes:Int?=null) {
        require(stopMinutes==null||stopMinutes in listOf(1,2,4,5,10,15))
        require(GpsRecordingService.currentKey==key);require(UUID.fromString(session).toString()==session);require(train.matches(Regex("[A-Za-z0-9]{1,12}")));require(manual.length()<=500)
        require(state==null||state?.key==key)
        state=State(key,session,train,JSONArray(manual.toString()),stopMinutes);tick(context)
    }
    @Synchronized fun context(key:String,session:String,train:String,manual:JSONArray) {
        val current=state?:return
        if(current.key==key&&current.session==session&&train.matches(Regex("[A-Za-z0-9]{1,12}"))&&manual.length()<=500){current.train=train;current.manual=JSONArray(manual.toString())}
    }
    @Synchronized fun status(key:String):JSONObject {
        val current=state?.takeIf { it.key==key }
        return JSONObject().put("sharing",current!=null).put("sharing_session",current?.session).put("shared_at",current?.sent?:0)
    }
    private fun request(session:String,body:JSONObject?,token:String):Int {
        val connection=URL(ApiClient.base()+"/api/v1/tf/gps-sharing/"+session).openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects=false;connection.requestMethod=if(body==null)"DELETE" else "PUT";connection.connectTimeout=5000;connection.readTimeout=10000
            connection.setRequestProperty("Authorization","Bearer $token");connection.setRequestProperty("Content-Type","application/json")
            if(body!=null){connection.doOutput=true;connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }}
            return connection.responseCode
        } finally {connection.disconnect()}
    }
    fun tick(context:Context) {
        val application=context.applicationContext;val current=state?:return
        if(System.currentTimeMillis()-current.attempted<300000||!busy.compareAndSet(false,true))return
        executor.execute {
            try {
                val points=GpsTrackStore(application).read(current.key);if(points.length()==0)return@execute
                val point=points.getJSONObject(points.length()-1);val now=System.currentTimeMillis()
                if(point.getDouble("accuracy")>50||now-point.getLong("t") !in -30000..120000)return@execute
                val snapshot=synchronized(this){if(state!==current)return@execute;current.attempted=now;current.train to JSONArray(current.manual.toString())}
                val token=TokenVault.token(application)?:return@execute
                val metrics=GpsLiveMetrics.calculate(points,snapshot.second,now,current.stopMinutes)
                val body=JSONObject(point.toString()).put("elapsed_ms",metrics.getLong("elapsed_ms")).put("stopped_ms",metrics.getLong("stopped_ms")).put("train_number",snapshot.first)
                val code=request(current.session,body,token)
                synchronized(this){if(state===current){if(code in 200..299)current.sent=now else if(code in listOf(401,403,409))state=null}}
            }catch(_:Exception){ /* Retry only with a current fix after the next five-minute interval. */ }
            finally{busy.set(false)}
        }
    }
    @Synchronized fun stop(context:Context,key:String?=null) {
        val current=state?:return;if(key!=null&&key!=current.key)return
        state=null
        val token=TokenVault.token(context)?:return
        executor.execute { runCatching { request(current.session,null,token) } }
    }
}
