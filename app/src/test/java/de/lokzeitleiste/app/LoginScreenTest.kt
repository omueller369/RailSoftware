package de.lokzeitleiste.app

import android.graphics.Bitmap
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import de.lokzeitleiste.app.network.AuthenticationRequired
import java.io.File
import java.io.IOException
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@OptIn(ExperimentalTestApi::class)
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], qualifiers = "w800dp-h1280dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class LoginScreenTest {
    @get:Rule val compose = createComposeRule()

    private fun show(reject: suspend () -> Nothing = { throw AuthenticationRequired() }) {
        compose.setContent {
            MaterialTheme {
                LanguageShell {
                    LoginScreen(authenticate = { _, _ -> reject() }, onSuccess = { _, _ -> error("No successful login expected") })
                }
            }
        }
    }
    private fun enter() {
        compose.onNodeWithText("TF-Nummer").performTextInput("787100")
        compose.onNodeWithText("Passwort", substring = false).performTextInput("wrong-password")
    }
    private fun attempt() {
        compose.onNodeWithText("Anmelden").performScrollTo().performClick()
        compose.waitForIdle()
    }
    private fun screenshot(name: String) {
        val directory = File("build/login-screenshots").apply { mkdirs() }
        File(directory, "$name.png").outputStream().use { output ->
            compose.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, output)
        }
    }
    @Test fun brandedCenteredLoginAndRecoveryAfterThreeRejectedAttempts() {
        show()
        compose.onNodeWithText("Rail Software").assertIsDisplayed()
        compose.onNodeWithContentDescription("Rail Software Logo").assertIsDisplayed()
        compose.onNodeWithText("Die Anmeldung bleibt auf diesem Gerät gespeichert.").assertExists()
        compose.onNodeWithText("Passwort vergessen").assertDoesNotExist()
        screenshot("tablet-login")
        enter();attempt();attempt()
        compose.onNodeWithText("Passwort vergessen").assertDoesNotExist()
        attempt()
        compose.onNodeWithText("Passwort vergessen").performScrollTo().performClick()
        compose.onNodeWithText("Wende Dich an Deinen Administrator", substring = true).assertIsDisplayed()
        compose.onNodeWithText("Verstanden").performClick()
        compose.onNodeWithText("TF-Nummer").performTextReplacement("787101")
        compose.onNodeWithText("Passwort vergessen").assertDoesNotExist()
    }
    @Test fun connectionFailuresDoNotEnablePasswordRecovery() {
        show { throw IOException("Offline") };enter();repeat(3) { attempt() }
        compose.onNodeWithText("Passwort vergessen").assertDoesNotExist()
    }
    @Test @Config(qualifiers = "w360dp-h800dp-mdpi")
    fun phoneFormRemainsScrollable() {
        show()
        compose.onNodeWithText("Anmelden").performScrollTo().assertIsDisplayed()
        screenshot("phone-login")
    }
}
