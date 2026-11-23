/* Regressionstests für gemeinsame Portaloberfläche. */
package de.lokzeitleiste.app.portal

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk=[35])
class OfflineSessionTest {
    private fun identity(id:Int,username:String)=JSONObject().put("username",username)
        .put("account",JSONObject().put("id",id).put("role","tf").put("password_change_required",false))
        .put("profile",JSONObject().put("id",id).put("first_name","Test"))
    @Test fun cachedSessionSurvivesRestartAndIsBoundToServerAndTf(){
        val app=RuntimeEnvironment.getApplication()
        val first=OfflineSession(app,"https://server.example","900001")
        first.save(identity(91,"900001"))
        assertEquals(91,OfflineSession(app,"https://server.example","900001").read()!!.getJSONObject("profile").getInt("id"))
        assertNull(OfflineSession(app,"https://other.example","900001").read())
        assertNull(OfflineSession(app,"https://server.example","900002").read())
    }
    @Test fun incompleteInitialPasswordAndMismatchedIdentitiesAreRejected(){
        val store=OfflineSession(RuntimeEnvironment.getApplication(),"https://invalid.example","900001")
        val value=identity(91,"900001");value.getJSONObject("account").put("password_change_required",true)
        store.save(value);assertNull(store.read())
        value.getJSONObject("account").put("password_change_required",false);value.getJSONObject("profile").put("id",92)
        store.save(value);assertNull(store.read())
        store.save(identity(91,"other"));assertNull(store.read())
    }
}
