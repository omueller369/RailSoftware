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
class GpsArchiveInfoTest {
    @Test fun inspectionCountsLogicalFixesWithoutChangingTheJournal(){
        val store=GpsTrackStore(RuntimeEnvironment.getApplication());val key="900001.archive-test"
        store.begin(key,true)
        for(t in listOf(10L,10L,20L))store.append(key,JSONObject().put("t",t).put("lat",52).put("lon",13))
        val info=store.summary(key)
        assertEquals(2,info.getInt("count"));assertEquals(20L,info.getLong("last"))
        assertEquals(3,store.read(key).length())
        store.erase(key);assertEquals(0,store.summary(key).getInt("count"))
    }
}
