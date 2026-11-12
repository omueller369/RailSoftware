package de.lokzeitleiste.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import de.lokzeitleiste.app.network.TokenVault
import de.lokzeitleiste.app.portal.PortalUpdater

/** Native login, followed by the same versioned TF portal used in the browser. */
class MainActivity : ComponentActivity() {
    private var loginUpdater:PortalUpdater?=null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        fun openPortal() { startActivity(Intent(this, TfPortalActivity::class.java)); finish() }
        if (TokenVault.username(this).isNotBlank()) { openPortal(); return }
        val updater=PortalUpdater(this,autoOffer=false);loginUpdater=updater
        setContent { MaterialTheme { LanguageShell { LoginScreen(updateAvailable=updater.updateAvailable,onUpdate={updater.check(true)}) { username, token ->
            TokenVault.save(this, username, token); openPortal()
        } } } }
        updater.check(false,force=true)
    }
    override fun onResume() { super.onResume();loginUpdater?.resume() }
}
