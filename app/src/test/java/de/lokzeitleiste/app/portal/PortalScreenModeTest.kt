package de.lokzeitleiste.app.portal

import android.view.WindowManager
import androidx.activity.ComponentActivity
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class PortalScreenModeTest {
    @Test fun fullScreenKeepsDisplayAwakeAndRestoresTimeout() {
        val controller=Robolectric.buildActivity(ComponentActivity::class.java).setup()
        val activity=controller.get()
        try {
            PortalScreenMode.apply(activity,true)
            assertTrue(activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON != 0)
            PortalScreenMode.apply(activity,false)
            assertEquals(0,activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } finally { controller.destroy() }
    }
}
