package de.lokzeitleiste.app.portal

import android.Manifest
import android.content.Intent
import android.location.Location
import android.location.LocationManager
import androidx.activity.ComponentActivity
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class DigiCommandBrowserTest {
    @Test fun browserLaunchDoesNotInterruptGpsJournal() {
        val app=RuntimeEnvironment.getApplication()
        shadowOf(app).grantPermissions(Manifest.permission.ACCESS_FINE_LOCATION)
        shadowOf(app.getSystemService(LocationManager::class.java)).setProviderEnabled(LocationManager.GPS_PROVIDER,true)
        val activity=Robolectric.buildActivity(ComponentActivity::class.java).setup()
        val controller=Robolectric.buildService(GpsRecordingService::class.java).create()
        val service=controller.get()
        val key="1.test-digi"
        try {
            service.onStartCommand(Intent().putExtra("key",key),0,1)
            fun fix(time:Long)=Location(LocationManager.GPS_PROVIDER).apply { this.time=time;latitude=52.0;longitude=13.0;accuracy=5f;speed=0f }
            service.onLocationChanged(fix(1794474000000L))
            DigiCommandBrowser.open(activity.get())
            assertEquals(DigiCommandBrowser.URL,shadowOf(activity.get()).nextStartedActivity.dataString)
            activity.pause().stop()
            service.onLocationChanged(fix(1794474005000L))
            assertEquals(key,GpsRecordingService.currentKey)
            assertEquals(2,GpsTrackStore(service).read(key).length())
        } finally { controller.destroy();activity.destroy() }
    }
}
