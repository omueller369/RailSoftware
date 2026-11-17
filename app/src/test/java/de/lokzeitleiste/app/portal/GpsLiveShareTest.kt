package de.lokzeitleiste.app.portal

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk=[35])
class GpsLiveShareTest {
    private fun point(t:Long)=JSONObject().put("t",t).put("lat",52.0).put("lon",13.0).put("accuracy",5).put("speed",0)
    @Test fun sharingRequiresExplicitConfigurationAndStopsLocally() {
        val app=RuntimeEnvironment.getApplication();val key="91.explicit-sharing"
        GpsRecordingService.currentKey=key
        try {
            GpsLiveShare.stop(app)
            GpsTrackStore(app).begin(key,true)
            assertFalse(GpsLiveShare.status(key).getBoolean("sharing"))
            GpsLiveShare.tick(app)
            assertFalse(GpsLiveShare.status(key).getBoolean("sharing"))
            GpsLiveShare.configure(app,key,"00000000-0000-4000-8000-000000000001","123",JSONArray(),1)
            assertTrue(GpsLiveShare.status(key).getBoolean("sharing"))
            assertFalse(GpsLiveShare.status("91.other-recording").getBoolean("sharing"))
            GpsLiveShare.stop(app,key)
            assertFalse(GpsLiveShare.status(key).getBoolean("sharing"))
        }finally{GpsLiveShare.stop(app);GpsRecordingService.currentKey=null}
    }
    @Test fun shortPauseBreaksAutomaticStandTime() {
        val base=1794744000000L
        val points=JSONArray();for(i in 0..25)points.put(point(base+i*5000).put("break_before",i==13))
        assertEquals(0L,GpsLiveMetrics.calculate(points,JSONArray(),base+125000,2).getLong("stopped_ms"))
    }
    @Test fun nativeTotalsHonorThresholdGapAndManualUnion() {
        val base=1794744000000L
        val points=JSONArray();for(i in 0..12)points.put(point(base+i*5000))
        assertEquals(60000L,GpsLiveMetrics.calculate(points,JSONArray(),base+60000,1).getLong("stopped_ms"))
        assertEquals(0L,GpsLiveMetrics.calculate(points,JSONArray(),base+60000,2).getLong("stopped_ms"))
        val manual=JSONArray().put(JSONObject().put("start",base+20000).put("end",base+50000))
        assertEquals(60000L,GpsLiveMetrics.calculate(points,manual,base+60000,1).getLong("stopped_ms"))
        val gap=JSONArray().put(point(base)).put(point(base+120000))
        assertEquals(0L,GpsLiveMetrics.calculate(gap,JSONArray(),base+120000,1).getLong("stopped_ms"))
        assertEquals(30000L,GpsLiveMetrics.calculate(gap,manual,base+120000,1).getLong("stopped_ms"))
    }
}
