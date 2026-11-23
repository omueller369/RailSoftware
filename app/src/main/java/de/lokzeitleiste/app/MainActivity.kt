/* Gemeinsame Verarbeitung für die gemeinsamen Anwendungsabläufe. */
package de.lokzeitleiste.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import de.lokzeitleiste.app.network.TokenVault
import de.lokzeitleiste.app.portal.PortalUpdater

/** Nach der nativen Anmeldung öffnet sich dasselbe versionierte TF-Portal wie im Browser. */
class MainActivity : ComponentActivity() {
    private var loginUpdater:PortalUpdater?=null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        fun openPortal() { startActivity(Intent(this, TfPortalActivity::class.java)); finish() }
        if (TokenVault.username(this).isNotBlank()) { openPortal(); return }
        val updater=PortalUpdater(this,autoOffer=false);loginUpdater=updater
        setContent { MaterialTheme { LanguageShell { LoginScreen(authenticate={ username,password ->
                val result=de.lokzeitleiste.app.network.ApiClient.login(username,password)
                val account=de.lokzeitleiste.app.network.ApiClient.identity(result.token)
                val profile=if(account.optBoolean("password_change_required"))org.json.JSONObject() else de.lokzeitleiste.app.network.ApiClient.portalIdentity(result.token)
                de.lokzeitleiste.app.portal.OfflineSession(this,de.lokzeitleiste.app.network.ApiClient.base(),result.username).save(org.json.JSONObject().put("account",account).put("profile",profile).put("username",result.username))
                result
            },updateAvailable=updater.updateAvailable,onUpdate={updater.check(true)}) { username, token ->
            TokenVault.save(this, username, token); openPortal()
        } } } }
        updater.check(false,force=true)
    }
    override fun onResume() { super.onResume();loginUpdater?.resume() }
}
