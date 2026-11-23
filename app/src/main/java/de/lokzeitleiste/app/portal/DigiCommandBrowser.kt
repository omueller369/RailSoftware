/* Gemeinsame Verarbeitung für Datenbankverbindungen und Transaktionen. */
package de.lokzeitleiste.app.portal

import android.content.Context
import android.content.Intent
import android.net.Uri

/** Der externe Browser läuft neben dem Portal; der GPS-Dienst bleibt aktiv. */
object DigiCommandBrowser {
    const val URL = "https://db.de/dibe"
    fun open(context: Context) { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(URL))) }
}
