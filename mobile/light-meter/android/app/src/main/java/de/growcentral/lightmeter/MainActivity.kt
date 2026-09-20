package de.growcentral.lightmeter

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.view.Surface
import android.view.TextureView
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import java.util.Locale
import kotlin.math.max

private enum class LightSource(val title: String, val ppfdPerLux: Double) {
    SUN("Sonnenlicht", 0.0185),
    WHITE_LED("Weiße LED (Vollspektrum)", 0.0150),
    WARM_LED("Warmweiße LED", 0.0140),
    HPS("Natriumdampf (HPS)", 0.0122),
    BLURPLE("Rot/Blau-LED (Blurple)", 0.0080)
}
private enum class MeasureTarget(val title: String, val factor: Double) {
    GRAY("Graukarte (18 %)", 1.0),
    PAPER("Weißes Papier", 0.2)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GrowLightMeterApp() }
    }
}

@Composable
private fun GrowLightMeterApp() {
    val context = LocalContext.current
    var cameraAllowed by remember {
        mutableStateOf(context.checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { cameraAllowed = it }
    LaunchedEffect(Unit) { if (!cameraAllowed) permission.launch(Manifest.permission.CAMERA) }

    var rawLux by remember { mutableDoubleStateOf(0.0) }
    var status by remember { mutableStateOf("Kamera wird vorbereitet …") }
    var source by remember { mutableStateOf(LightSource.WHITE_LED) }
    var target by remember { mutableStateOf(MeasureTarget.PAPER) }
    var calibration by remember { mutableDoubleStateOf(1.0) }
    var hours by remember { mutableDoubleStateOf(18.0) }
    var frozenLux by remember { mutableStateOf<Double?>(null) }

    val liveLux = rawLux * target.factor * calibration
    val lux = frozenLux ?: liveLux
    val ppfd = lux * source.ppfdPerLux
    val dli = ppfd * hours * 3600.0 / 1_000_000.0

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF41E7C3),
            secondary = Color(0xFF79FF42),
            background = Color(0xFF020608),
            surface = Color(0xFF0B1417)
        )
    ) {
        Surface(Modifier.fillMaxSize()) {
            BoxWithConstraints(Modifier.fillMaxSize()) {
                if (maxWidth >= 700.dp) {
                    Row(Modifier.padding(20.dp), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                            CameraCard(cameraAllowed, { rawLux = it }, { status = it })
                            ResultCard(lux, ppfd, frozenLux != null) { frozenLux = if (frozenLux == null) liveLux else null }
                        }
                        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                            SettingsCard(source, target, calibration, { source = it }, { target = it }, { calibration = it })
                            DliCard(hours, dli) { hours = it }
                            HintCard(status)
                        }
                    }
                } else {
                    Column(
                        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        CameraCard(cameraAllowed, { rawLux = it }, { status = it })
                        ResultCard(lux, ppfd, frozenLux != null) { frozenLux = if (frozenLux == null) liveLux else null }
                        SettingsCard(source, target, calibration, { source = it }, { target = it }, { calibration = it })
                        DliCard(hours, dli) { hours = it }
                        HintCard(status)
                    }
                }
            }
        }
    }
}

@Composable
private fun CameraCard(allowed: Boolean, onLux: (Double) -> Unit, onStatus: (String) -> Unit) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(220.dp), contentAlignment = Alignment.Center) {
            if (allowed) {
                AndroidView(
                    modifier = Modifier.fillMaxSize(),
                    factory = { CameraMeterTextureView(it, onLux, onStatus) },
                    update = { it.updateCallbacks(onLux, onStatus) }
                )
                Text("◎", color = Color.White, fontSize = 36.sp)
            } else {
                Text("Kamerazugriff wird benötigt.")
            }
        }
    }
}

@Composable
private fun ResultCard(lux: Double, ppfd: Double, frozen: Boolean, onToggle: () -> Unit) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("PPFD (geschätzt)")
            Text(String.format(Locale.US, "%.0f", ppfd), fontSize = 64.sp)
            Text("µmol/m²/s", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("${lux.toInt()} lux · ${stage(ppfd)}", modifier = Modifier.padding(top = 6.dp))
            Button(onClick = onToggle, modifier = Modifier.padding(top = 12.dp)) {
                Text(if (frozen) "Weiter messen" else "Wert halten")
            }
        }
    }
}

@Composable
private fun SettingsCard(
    source: LightSource,
    target: MeasureTarget,
    calibration: Double,
    onSource: (LightSource) -> Unit,
    onTarget: (MeasureTarget) -> Unit,
    onCalibration: (Double) -> Unit
) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Messung", style = MaterialTheme.typography.titleMedium)
            EnumMenu("Lichtquelle", source.title, LightSource.entries.map { it.title }) { title ->
                onSource(LightSource.entries.first { it.title == title })
            }
            EnumMenu("Messfläche", target.title, MeasureTarget.entries.map { it.title }) { title ->
                onTarget(MeasureTarget.entries.first { it.title == title })
            }
            Text("Kalibrierfaktor: ${String.format(Locale.US, "%.2f", calibration)}")
            Slider(value = calibration.toFloat(), onValueChange = { onCalibration(it.toDouble()) }, valueRange = 0.2f..5.0f)
        }
    }
}

@Composable
private fun EnumMenu(label: String, current: String, items: List<String>, onPick: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        Text(label, style = MaterialTheme.typography.labelMedium)
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) { Text(current) }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            items.forEach { item ->
                DropdownMenuItem(text = { Text(item) }, onClick = { expanded = false; onPick(item) })
            }
        }
    }
}

@Composable
private fun DliCard(hours: Double, dli: Double, onHours: (Double) -> Unit) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text("Tageslichtintegral (DLI)", style = MaterialTheme.typography.titleMedium)
            Slider(value = hours.toFloat(), onValueChange = { onHours(it.toDouble()) }, valueRange = 1f..24f, steps = 22)
            Text("${hours.toInt()} h Licht pro Tag → ${String.format(Locale.US, "%.1f", dli)} mol/m²/Tag")
        }
    }
}

@Composable
private fun HintCard(status: String) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("So misst du", style = MaterialTheme.typography.titleMedium)
            Text("Lege ein weißes Blatt Papier auf Höhe der Pflanzenspitzen unter die Lampe und halte das Gerät etwa 20–30 cm darüber, Kamera nach unten, ohne Schatten auf das Papier zu werfen. Für genauere Werte mit einem Referenz-Luxmeter oder Quantum-Meter kalibrieren.")
            Text(status, color = MaterialTheme.colorScheme.primary)
        }
    }
}

private fun stage(ppfd: Double) = when {
    ppfd < 100 -> "sehr schwach"
    ppfd < 300 -> "Sämlinge / Stecklinge"
    ppfd < 600 -> "Wachstumsphase"
    ppfd < 1000 -> "Blüte / Fruchtung"
    else -> "sehr hoch"
}

private class CameraMeterTextureView(
    context: Context,
    private var onLux: (Double) -> Unit,
    private var onStatus: (String) -> Unit
) : TextureView(context), TextureView.SurfaceTextureListener {
    private val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    private var camera: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private val samples = ArrayDeque<Double>()

    init { surfaceTextureListener = this }

    fun updateCallbacks(lux: (Double) -> Unit, status: (String) -> Unit) {
        onLux = lux
        onStatus = status
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        startThread()
        if (isAvailable) openCamera()
    }

    override fun onDetachedFromWindow() {
        closeCamera()
        stopThread()
        super.onDetachedFromWindow()
    }

    override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) = openCamera()
    override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) = Unit
    override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean { closeCamera(); return true }
    override fun onSurfaceTextureUpdated(surface: SurfaceTexture) = Unit

    private fun startThread() {
        if (thread == null) {
            thread = HandlerThread("GrowLightMeterCamera").also { it.start() }
            handler = Handler(thread!!.looper)
        }
    }

    private fun stopThread() {
        thread?.quitSafely()
        thread = null
        handler = null
    }

    private fun openCamera() {
        if (!isAvailable || camera != null || context.checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return
        try {
            val id = manager.cameraIdList.firstOrNull {
                manager.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
            } ?: manager.cameraIdList.first()
            manager.openCamera(id, object : CameraDevice.StateCallback() {
                override fun onOpened(device: CameraDevice) { camera = device; createSession() }
                override fun onDisconnected(device: CameraDevice) { device.close(); camera = null }
                override fun onError(device: CameraDevice, error: Int) {
                    device.close()
                    camera = null
                    post { onStatus("Kamerafehler: $error") }
                }
            }, handler)
        } catch (e: Exception) {
            post { onStatus("Kamera konnte nicht geöffnet werden: ${e.localizedMessage}") }
        }
    }

    private fun createSession() {
        val device = camera ?: return
        val texture = surfaceTexture ?: return
        texture.setDefaultBufferSize(1280, 720)
        val surface = Surface(texture)
        try {
            val request = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                addTarget(surface)
                set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)
                set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
            }
            device.createCaptureSession(listOf(surface), object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(s: CameraCaptureSession) {
                    session = s
                    s.setRepeatingRequest(request.build(), captureCallback, handler)
                    post { onStatus("Messung aktiv") }
                }
                override fun onConfigureFailed(s: CameraCaptureSession) {
                    post { onStatus("Kamera-Session fehlgeschlagen") }
                }
            }, handler)
        } catch (e: Exception) {
            post { onStatus("Kamera-Session: ${e.localizedMessage}") }
        }
    }

    private val captureCallback = object : CameraCaptureSession.CaptureCallback() {
        override fun onCaptureCompleted(session: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
            val iso = result.get(CaptureResult.SENSOR_SENSITIVITY)?.toDouble() ?: return
            val ns = result.get(CaptureResult.SENSOR_EXPOSURE_TIME)?.toDouble() ?: return
            val aperture = result.get(CaptureResult.LENS_APERTURE)?.toDouble() ?: return
            if (iso <= 0 || ns <= 0 || aperture <= 0) return
            val estimate = 250.0 * aperture * aperture / ((ns / 1_000_000_000.0) * iso)
            if (!estimate.isFinite() || estimate <= 0) return

            samples.addLast(estimate)
            while (samples.size > 12) samples.removeFirst()
            val sorted = samples.sorted()
            val trimmed = if (sorted.size >= 6) sorted.drop(1).dropLast(1) else sorted
            post { onLux(max(0.0, trimmed.average())) }
        }
    }

    private fun closeCamera() {
        try { session?.close() } catch (_: Exception) {}
        try { camera?.close() } catch (_: Exception) {}
        session = null
        camera = null
        samples.clear()
    }
}
