#!/usr/bin/env python3
"""Step 376: harden the reference-driven launcher UI for low-RAM Android devices.

Keeps the requested visual flow while reducing bitmap memory, animation work and
Activity lifetime leaks. The first-run action performs real writable-storage and
download-path readiness checks rather than only creating a fake completion marker.
"""
from pathlib import Path
import re
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
REMOTE_BG = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/San_Diego_mountains_at_night_%28Unsplash%29.jpg/1280px-San_Diego_mountains_at_night_%28Unsplash%29.jpg"


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit("[step376] expected exactly one DroidLauncherUiActivity.kt")
    return hits[0]


def method_span(src: str, sig: str) -> tuple[int, int]:
    start = src.find(sig)
    if start < 0:
        raise SystemExit("[step376] missing method: " + sig)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("[step376] missing opening brace: " + sig)
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
        if state == "line":
            if c == "\n":
                state = "code"
            i += 1
            continue
        if state == "block":
            if c == "*" and n == "/":
                state = "code"
                i += 2
            else:
                i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"':
                state = "code"
                i += 3
            else:
                i += 1
            continue
        if state == "string":
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                state = "code"
            i += 1
            continue
        if c == "/" and n == "/":
            state = "line"
            i += 2
            continue
        if c == "/" and n == "*":
            state = "block"
            i += 2
            continue
        if c == '"' and n == '"' and n2 == '"':
            state = "triple"
            i += 3
            continue
        if c == '"':
            state = "string"
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise SystemExit("[step376] unterminated method: " + sig)


def replace_method(src: str, sig: str, replacement: str) -> str:
    a, b = method_span(src, sig)
    return src[:a] + replacement + src[b:]


HELPERS = r'''
    private val step376LowRam: Boolean by lazy {
        val manager = getSystemService(android.content.Context.ACTIVITY_SERVICE) as? android.app.ActivityManager
        manager?.isLowRamDevice == true
    }
    private var step376BgThread: Thread? = null
    private var step376Glow: android.animation.ValueAnimator? = null

    private fun step376PrepareFirstRun(onResult: (Boolean, String) -> Unit) {
        Thread {
            try {
                val root = java.io.File(filesDir, "droid-launcher")
                val dirs = listOf(
                    java.io.File(root, "launcher-components"),
                    java.io.File(root, "instances"),
                    java.io.File(root, "downloads"),
                    java.io.File(root, "content"),
                    java.io.File(root, "runtimes")
                )
                dirs.forEach { dir ->
                    if (!dir.exists() && !dir.mkdirs()) throw java.io.IOException("Could not create " + dir.name)
                    if (!dir.isDirectory || !dir.canWrite()) throw java.io.IOException("Launcher storage is not writable: " + dir.name)
                }
                val probe = java.io.File(root, "readiness.txt")
                probe.writeText("storage=ready\ninstances=ready\ndownloads=ready\ncontent=ready\nruntimes=on-demand\n")
                if (!probe.isFile() || probe.length() == 0L) throw java.io.IOException("Launcher readiness verification failed")
                runOnUiThread { onResult(true, "Launcher storage is ready. Runtime components can be installed on demand.") }
            } catch (t: Throwable) {
                runOnUiThread { onResult(false, t.message ?: "Launcher preparation failed") }
            }
        }.apply { isDaemon = true; start() }
    }

    private fun step376LoadBackground(target: android.widget.ImageView) {
        val cache = java.io.File(cacheDir, "droid-launcher-background.jpg")
        fun decode(path: java.io.File): android.graphics.Bitmap? {
            if (!path.isFile()) return null
            val bounds = android.graphics.BitmapFactory.Options().apply { inJustDecodeBounds = true }
            android.graphics.BitmapFactory.decodeFile(path.absolutePath, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
            val maxDimension = if (step376LowRam) 640 else 960
            var sample = 1
            while (bounds.outWidth / sample > maxDimension || bounds.outHeight / sample > maxDimension) sample *= 2
            val opts = android.graphics.BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
            }
            return android.graphics.BitmapFactory.decodeFile(path.absolutePath, opts)
        }
        step376BgThread = Thread {
            try {
                var bitmap = decode(cache)
                if (bitmap == null) {
                    val temp = java.io.File(cacheDir, "droid-launcher-background.tmp")
                    val c = java.net.URL("''' + REMOTE_BG + '''").openConnection() as java.net.HttpURLConnection
                    c.connectTimeout = 5000
                    c.readTimeout = 8000
                    c.instanceFollowRedirects = true
                    c.setRequestProperty("User-Agent", "DroidLauncher/1.0")
                    try {
                        if (c.responseCode in 200..299) {
                            c.inputStream.use { input ->
                                java.io.FileOutputStream(temp).use { output -> input.copyTo(output, 64 * 1024) }
                            }
                            if (temp.isFile && temp.length() > 0L) {
                                if (cache.exists()) cache.delete()
                                temp.renameTo(cache)
                                bitmap = decode(cache)
                            }
                        }
                    } finally {
                        c.disconnect()
                        if (temp.exists() && !cache.exists()) temp.delete()
                    }
                }
                if (bitmap != null) {
                    val finalBitmap = bitmap
                    runOnUiThread {
                        if (!isFinishing && !isDestroyed) target.setImageBitmap(finalBitmap)
                        else finalBitmap.recycle()
                    }
                }
            } catch (_: Throwable) {
            } finally {
                step376BgThread = null
            }
        }.apply { isDaemon = true; start() }
    }

    private fun step376StartGlow(view: android.view.View) {
        if (step376LowRam) {
            view.alpha = 0.28f
            return
        }
        step376Glow?.cancel()
        step376Glow = android.animation.ObjectAnimator.ofFloat(view, "alpha", .2f, .72f, .2f).apply {
            duration = 5200
            repeatCount = android.animation.ValueAnimator.INFINITE
            start()
        }
    }

    private fun step376PauseEffects() {
        try { step376Glow?.pause() } catch (_: Throwable) {}
        if (!step376LowRam) {
            try { if (step375Track?.playState == android.media.AudioTrack.PLAYSTATE_PLAYING) step375Track?.pause() } catch (_: Throwable) {}
        }
    }

    private fun step376ResumeEffects() {
        if (!step376LowRam) {
            try { step375Track?.play() } catch (_: Throwable) {}
            try { step376Glow?.resume() } catch (_: Throwable) {}
        }
    }

    private fun step376ReleaseEffects() {
        try { step376Glow?.cancel() } catch (_: Throwable) {}
        step376Glow = null
        try { step375Track?.stop(); step375Track?.release() } catch (_: Throwable) {}
        step375Track = null
        try { step376BgThread?.interrupt() } catch (_: Throwable) {}
        step376BgThread = null
    }
'''


def patch_build(src: str) -> str:
    a, b = method_span(src, "    private fun buildUi()")
    body = src[a:b]
    # Remove Step 375's eager full-resolution network decode.
    body = re.sub(r"\n\s*Thread\s*\{.*?\n\s*\}\.start\(\)", "", body, count=1, flags=re.S)
    body = re.sub(r"\n\s*android\.animation\.ObjectAnimator\.ofFloat\(glow, \"alpha\",.*?start\(\) \}", "", body, count=1, flags=re.S)
    body = body.replace("        setContentView(root)", "        setContentView(root)\n        step376LoadBackground(bg)\n        step376StartGlow(glow)", 1)
    return src[:a] + body + src[b:]


def patch_first_run(src: str) -> str:
    sig = "    private fun step375FirstRun()"
    a, b = method_span(src, sig)
    body = src[a:b]
    body = body.replace("FIRST-LAUNCH COMPONENTS", "FIRST-LAUNCH RUNTIME", 1)
    body = body.replace(
        "authlib-injector\\ncaciocavallo\\nInternal Java 8 / 17 / 21 / 25\\nJNA\\nLauncher components\\nLWJGL\\nNative renderer\\nMinecraft runtime preparation",
        "Auth support\\nJava 8 / 17 / 21 / 25 runtimes\\nJNA / GUI backend\\nNative renderer\\nMinecraft runtime\\nDownload-ready on demand",
        1,
    )
    pattern = re.compile(r'(?s)        left\.addView\(step375Button\("INSTALL", true\).*?        left\.addView\(step375Button\("LEAVE FOR NOW"')
    replacement = '''        left.addView(step375Button("INSTALL", true) {
            android.app.AlertDialog.Builder(this).setTitle("Preparing launcher")
                .setMessage("Checking launcher storage and download paths…")
                .setCancelable(false).create().also { dialog ->
                    dialog.show()
                    step376PrepareFirstRun { success, message ->
                        dialog.dismiss()
                        if (success) {
                            step375Prefs().edit().putBoolean("installed", true).apply()
                            android.widget.Toast.makeText(this@DroidLauncherUiActivity, message, android.widget.Toast.LENGTH_LONG).show()
                            showPage("Home")
                        } else {
                            android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Preparation failed: " + message, android.widget.Toast.LENGTH_LONG).show()
                        }
                    }
                }
        }, LinearLayout.LayoutParams(-1, dp(50)))
        left.addView(step375Button("LEAVE FOR NOW"'''
    body, n = pattern.subn(replacement, body, count=1)
    if n != 1:
        raise SystemExit("[step376] first-run INSTALL block not found")
    return src[:a] + body + src[b:]


def patch_panel_button(src: str) -> str:
    src = src.replace(
        "        elevation = dp(8).toFloat()",
        "        elevation = if (step376LowRam) dp(2).toFloat() else dp(8).toFloat()",
        1,
    )
    old = '        elevation = dp(5).toFloat(); setOnClickListener { animate().scaleX(.96f).scaleY(.96f).setDuration(70).withEndAction { scaleX = 1f; scaleY = 1f; action() }.start() }'
    if old in src:
        new = '''        elevation = if (step376LowRam) dp(1).toFloat() else dp(5).toFloat()
        setOnClickListener {
            if (step376LowRam) action()
            else animate().scaleX(.96f).scaleY(.96f).setDuration(70).withEndAction { scaleX = 1f; scaleY = 1f; action() }.start()
        }'''
        src = src.replace(old, new, 1)
    return src


def patch_music(src: str) -> str:
    sig = "    private fun step375StartMusic()"
    if sig not in src:
        return src
    a, b = method_span(src, sig)
    body = '''    private fun step375StartMusic() {
        if (step376LowRam || step375Track != null) return
        try {
            val rate = 22050
            val len = rate * 4
            val pcm = ShortArray(len)
            val notes = doubleArrayOf(55.0, 65.406, 73.416, 82.407)
            for (i in pcm.indices) {
                val t = i.toDouble() / rate
                val f = notes[(i / (rate * 2)) % notes.size]
                val x = (.08 * kotlin.math.sin(2 * Math.PI * f * t) + .025 * kotlin.math.sin(4 * Math.PI * f * t))
                pcm[i] = (x * 32767).toInt().coerceIn(-32768, 32767).toShort()
            }
            step375Track = android.media.AudioTrack(
                android.media.AudioManager.STREAM_MUSIC, rate,
                android.media.AudioFormat.CHANNEL_OUT_MONO,
                android.media.AudioFormat.ENCODING_PCM_16BIT,
                pcm.size * 2, android.media.AudioTrack.MODE_STATIC
            ).apply {
                write(pcm, 0, pcm.size)
                setLoopPoints(0, pcm.size, -1)
                setVolume(.08f)
                play()
            }
        } catch (_: Throwable) {
            step375Track = null
        }
    }'''
    return src[:a] + body + src[b:]


def patch_lifecycle(src: str) -> str:
    src = replace_method(src, "    override fun onPause()", '''    override fun onPause() {
        step376PauseEffects()
        super.onPause()
    }''')
    src = replace_method(src, "    override fun onResume()", '''    override fun onResume() {
        super.onResume()
        step376ResumeEffects()
    }''')
    src = replace_method(src, "    override fun onDestroy()", '''    override fun onDestroy() {
        step376ReleaseEffects()
        super.onDestroy()
    }''')
    return src


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")

    if "private val step376LowRam" not in source:
        insert = source.find("    override fun onCreate(")
        if insert < 0:
            raise SystemExit("[step376] onCreate anchor missing")
        source = source[:insert] + HELPERS + "\n" + source[insert:]

    source = patch_build(source)
    source = patch_first_run(source)
    source = patch_panel_button(source)
    source = patch_music(source)
    source = patch_lifecycle(source)

    required = (
        "private val step376LowRam",
        "step376PrepareFirstRun",
        "readiness.txt",
        "droid-launcher-background.jpg",
        "inPreferredConfig = android.graphics.Bitmap.Config.RGB_565",
        "manager?.isLowRamDevice == true",
        "step376StartGlow",
        "step376ReleaseEffects",
    )
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit("[step376] missing final UI contract(s): " + ", ".join(missing))
    if 'writeText("installed")' in source or "writeText('installed')" in source:
        raise SystemExit("[step376] fake first-run completion marker remains")
    ui.write_text(source, encoding="utf-8")

    print("[step376] low-RAM UI/animation/background hardening applied")
    print("[step376] first-run now verifies real writable launcher storage before completion")
    print("[step376] remote background is cached and decoded with RGB_565 sampling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
