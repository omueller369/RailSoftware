package de.lokzeitleiste.app

import android.graphics.Paint
import android.graphics.Path
import android.graphics.PathMeasure
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import de.lokzeitleiste.app.data.migrateAccountData
import de.lokzeitleiste.app.network.ApiClient
import de.lokzeitleiste.app.network.AuthenticationRequired
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import org.json.JSONObject

private object LoginText {
    const val title = "text_39ed724e98ad"
    const val logo = "text_57488d0fc1fa"
    const val intro = "text_42d99ab79c2f"
    const val initial = "text_039ace479358"
    const val number = "text_c25434cdbbfc"
    const val password = "text_82262fb90295"
    const val login = "text_8b905ef99721"
    const val busy = "text_42f30e8527f6"
    const val forgot = "text_83508ad01fae"
    const val stored = "text_1f52a6bede08"
    const val rejected = "text_04057a112b54"
    const val failed = "text_7d734939a338"
    const val recovery = "text_d91c8e148e7b"
    const val ok = "text_d37b853faffe"
}

/** Rounded, parallel rails with sleepers, using the logo's burgundy and navy. */
private fun Modifier.railFrame() = drawWithCache {
    val burgundy = android.graphics.Color.rgb(164, 0, 39)
    val navy = android.graphics.Color.rgb(0, 43, 76)
    fun rail(inset: Float, radius: Float) = Path().apply {
        addRoundRect(inset, inset, size.width-inset, size.height-inset, radius, radius, Path.Direction.CW)
    }
    val centre = rail(13.dp.toPx(), 23.dp.toPx())
    val measure = PathMeasure(centre, true)
    val outer = rail(8.dp.toPx(), 28.dp.toPx())
    val inner = rail(18.dp.toPx(), 18.dp.toPx())
    val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeCap = Paint.Cap.ROUND; strokeWidth = 2.dp.toPx() }
    val point = FloatArray(2)
    val tangent = FloatArray(2)
    val halfSleeper = 9.dp.toPx()
    val count = (measure.length / 21.dp.toPx()).toInt().coerceAtLeast(1)
    onDrawBehind {
        drawIntoCanvas { canvas ->
            val native = canvas.nativeCanvas
            repeat(count) { index ->
                measure.getPosTan(measure.length*index/count, point, tangent)
                val nx = -tangent[1]*halfSleeper
                val ny = tangent[0]*halfSleeper
                paint.color = if (index % 2 == 0) burgundy else navy
                native.drawLine(point[0]-nx, point[1]-ny, point[0]+nx, point[1]+ny, paint)
            }
            paint.color = burgundy; native.drawPath(outer, paint)
            paint.color = navy; native.drawPath(inner, paint)
        }
    }
}

@Composable
fun LoginScreen(
    authenticate: suspend (String, String) -> ApiClient.LoginResult = ApiClient::login,
    onSuccess: (String, String) -> Unit
) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var credentialsRejected by remember { mutableStateOf(false) }
    var failures by rememberSaveable(username) { mutableIntStateOf(0) }
    var showRecovery by rememberSaveable { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var pending by remember { mutableStateOf<ApiClient.LoginResult?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val language = LocalLanguage.current.takeIf { it in LanguageRuntime.codes } ?: "de"
    val strings = remember(context, language) {
        JSONObject(context.assets.open("tf-portal/native-login/$language.json").bufferedReader().use { it.readText() })
    }
    fun text(key: String) = strings.getString(key)
    val keyboard = LocalSoftwareKeyboardController.current
    pending?.let { account ->
        PasswordChangeScreen(account.username, account.token, mandatory = true,
            onSuccess = { name, token -> pending = null; onSuccess(name, token) },
            onCancel = { scope.launch { runCatching { ApiClient.logout(account.token) } }; pending = null })
        return
    }
    val validNumber = username.matches(Regex("[1-9][0-9]{5}"))
    val submit: () -> Unit = {
        if (!busy && validNumber && password.isNotBlank()) {
            busy = true; message = ""; keyboard?.hide()
            scope.launch {
                try {
                    val result = authenticate(username, password)
                    migrateAccountData(context, result.previousUsername, result.username)
                    password = ""; failures = 0; credentialsRejected = false
                    if (result.passwordChangeRequired) pending = result else onSuccess(result.username, result.token)
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (error: Exception) {
                    credentialsRejected = error is AuthenticationRequired
                    if (credentialsRejected) failures = (failures+1).coerceAtMost(3)
                    message = if (credentialsRejected) LoginText.rejected else LoginText.failed
                } finally { busy = false }
            }
        }
    }
    if (showRecovery) AlertDialog(
        onDismissRequest = { showRecovery = false },
        title = { Text(text(LoginText.forgot)) },
        text = { Text(text(LoginText.recovery)) },
        confirmButton = { TextButton(onClick = { showRecovery = false }) { Text(text(LoginText.ok)) } }
    )
    BoxWithConstraints(Modifier.fillMaxSize().imePadding().background(Color(0xFFF1F4F7))) {
        val availableHeight = maxHeight
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).heightIn(min = availableHeight).padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Column(
                Modifier.widthIn(max = 440.dp).fillMaxWidth().background(Color.White, RoundedCornerShape(36.dp)).railFrame().padding(34.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Image(painterResource(R.drawable.rail_software_foreground), contentDescription = text(LoginText.logo), modifier = Modifier.size(112.dp))
                Text(text(LoginText.title), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = Color(0xFF002B4C), textAlign = TextAlign.Center)
                Text(text(LoginText.intro), style = MaterialTheme.typography.bodyMedium, color = Color(0xFF002B4C), textAlign = TextAlign.Center)
                Text(text(LoginText.initial), style = MaterialTheme.typography.bodySmall, color = Color(0xFF495E6E), textAlign = TextAlign.Center)
                OutlinedTextField(username, { credentialsRejected = false; message = ""; username = it.filter(Char::isDigit).take(6) },
                    modifier = Modifier.fillMaxWidth(), enabled = !busy, label = { Text(text(LoginText.number)) },
                    isError = credentialsRejected, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Next))
                OutlinedTextField(password, { credentialsRejected = false; message = ""; password = it },
                    modifier = Modifier.fillMaxWidth(), enabled = !busy, label = { Text(text(LoginText.password)) },
                    isError = credentialsRejected, singleLine = true, visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { submit() }))
                if (message.isNotBlank()) Text(text(message), color = MaterialTheme.colorScheme.error, textAlign = TextAlign.Center)
                Button(onClick = submit, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    enabled = !busy && validNumber && password.isNotBlank(), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF002B4C))) {
                    Text(text(if (busy) LoginText.busy else LoginText.login))
                }
                if (failures >= 3) OutlinedButton(onClick = { showRecovery = true }, enabled = !busy,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFA40027))) { Text(text(LoginText.forgot), textAlign = TextAlign.Center) }
                Text(text(LoginText.stored), style = MaterialTheme.typography.bodySmall, color = Color(0xFF495E6E), textAlign = TextAlign.Center)
            }
        }
    }
}
