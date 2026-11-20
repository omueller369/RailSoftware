package de.lokzeitleiste.app.portal

import android.content.Context
import org.json.JSONObject

/** Last online-verified identity, scoped to server and authenticated native username. */
class OfflineSession(context: Context, private val origin: String, private val username: String) {
    private val preferences=context.getSharedPreferences("portal_identity",Context.MODE_PRIVATE)
    private val key="$origin|$username"
    fun read(): JSONObject? = runCatching {
        val value=JSONObject(preferences.getString(key,null)?:return@runCatching null)
        val account=value.getJSONObject("account");val profile=value.getJSONObject("profile")
        require(value.getString("username")==username && account.getString("role")=="tf")
        require(account.getInt("id")>0 && !account.optBoolean("password_change_required"))
        require(profile.getInt("id")==account.getInt("id"))
        value
    }.getOrNull()
    fun save(value: JSONObject) { preferences.edit().putString(key,value.toString()).commit() }
}
