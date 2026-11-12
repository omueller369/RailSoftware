package de.lokzeitleiste.app.portal

import android.content.Context
import android.content.Intent
import android.net.Uri

/** External browser only; the portal and its GPS foreground service stay alive. */
object DigiCommandBrowser {
    const val URL = "https://db.de/dibe"
    fun open(context: Context) { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(URL))) }
}
