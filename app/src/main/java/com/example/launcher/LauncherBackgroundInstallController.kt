package com.example.launcher

import android.content.Context
import android.net.Uri
import android.os.Handler
import android.os.Looper
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * Background controller for installs/imports.
 * At most one task runs for a logical key; Minecraft installs wait for the
 * underlying asynchronous installer to report completion before succeeding.
 * UI listeners are always called on the Android main thread.
 */
object LauncherBackgroundInstallController {
    enum class Kind { MINECRAFT_VERSION, MODPACK, MOD, SHADER, RESOURCE_PACK, WORLD }
    enum class State { QUEUED, RUNNING, SUCCESS, FAILED }
    data class TaskState(val key: String, val kind: Kind, val state: State, val message: String)

    private const val LATEST = "latest"
    private const val LATEST_TIMEOUT_SECONDS = 30L
    private const val COMPLETED_STATE_RETENTION_MS = 10 * 60 * 1000L
    private const val MAX_STAGED_CONTENT_BYTES = 1L * 1024L * 1024L * 1024L
    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "DroidLauncher-BackgroundInstall").apply {
            isDaemon = true
            priority = Thread.NORM_PRIORITY - 1
        }
    }
    private val mainHandler = Handler(Looper.getMainLooper())
    private val active = ConcurrentHashMap<String, TaskState>()

    fun state(key: String): TaskState? = active[key]

    fun installMinecraft(context: Context, version: String, listener: (TaskState) -> Unit = {}) {
        val requested = version.trim().ifBlank { LATEST }
        val key = "minecraft:$requested"
        submit(key, Kind.MINECRAFT_VERSION, listener) {
            val actualVersion = resolveVersion(context, requested) ?:
                throw IllegalStateException("Could not resolve Minecraft latest release")
            val done = CountDownLatch(1)
            val failure = AtomicReference<Throwable?>(null)
            MinecraftVersionInstallManager.install(context, actualVersion, object : MinecraftVersionInstallManager.Listener {
                override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                    publish(TaskState(key, Kind.MINECRAFT_VERSION, State.RUNNING, progress.stage), listener)
                }
                override fun onComplete(version: String) { done.countDown() }
                override fun onError(version: String, error: Throwable) {
                    failure.set(error)
                    done.countDown()
                }
            })
            if (!done.await(6, TimeUnit.HOURS)) throw IllegalStateException("Minecraft installation timed out")
            failure.get()?.let { throw it }
        }
    }

    fun importContent(context: Context, kind: Kind, source: File, listener: (TaskState) -> Unit = {}) {
        val key = "${kind.name.lowercase()}:${source.canonicalPath}"
        submit(key, kind, listener) {
            performContentImport(context, kind, source)
        }
    }

    /** Stages an Android document URI and imports it entirely off the UI thread. */
    fun importContentUri(
        context: Context,
        kind: Kind,
        uri: Uri,
        listener: (TaskState) -> Unit = {}
    ) {
        val key = "${kind.name.lowercase()}:uri:${uri}"
        submit(key, kind, listener) {
            val resolver = context.contentResolver
            val displayName = resolver.query(
                uri,
                arrayOf(android.provider.OpenableColumns.DISPLAY_NAME),
                null,
                null,
                null
            )?.use { cursor ->
                if (cursor.moveToFirst()) cursor.getString(0) else null
            }?.takeIf { it.isNotBlank() } ?: "selected-content.tmp"
            val suffix = displayName.substringAfterLast(".", "")
                .takeIf { it.length in 1..12 && it.all(Char::isLetterOrDigit) }
                ?.let { ".$it" } ?: ".tmp"

            val temp = File.createTempFile("droid-content-", suffix, context.cacheDir)
            try {
                resolver.query(
                    uri,
                    arrayOf(android.provider.OpenableColumns.SIZE),
                    null,
                    null,
                    null
                )?.use { cursor ->
                    if (cursor.moveToFirst() && !cursor.isNull(0)) {
                        val declared = cursor.getLong(0)
                        if (declared > MAX_STAGED_CONTENT_BYTES) {
                            throw IOException("Selected content exceeds the 1 GiB safety limit")
                        }
                    }
                }
                resolver.openInputStream(uri)?.use { input ->
                    FileOutputStream(temp, false).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        var total = 0L
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            if (count == 0) continue
                            total += count
                            if (total > MAX_STAGED_CONTENT_BYTES) {
                                throw IOException("Selected content exceeds the 1 GiB safety limit")
                            }
                            output.write(buffer, 0, count)
                        }
                        output.fd.sync()
                    }
                } ?: throw IOException("Could not open selected content")
                performContentImport(context, kind, temp)
            } finally {
                if (temp.exists() && !temp.delete()) temp.deleteOnExit()
            }
        }
    }

    private fun performContentImport(context: Context, kind: Kind, source: File) {
        when (kind) {
            Kind.MODPACK -> {
                if (source.extension.equals("mrpack", true)) {
                    MinecraftModpackManager.install(context, source)
                } else {
                    MinecraftContentManager.importArchive(context, MinecraftContentManager.Kind.MODPACK, source)
                }
            }
            Kind.WORLD -> MinecraftContentManager.importArchive(context, MinecraftContentManager.Kind.WORLD, source)
            Kind.MOD, Kind.SHADER, Kind.RESOURCE_PACK ->
                MinecraftContentManager.importFile(context, MinecraftContentManager.Kind.valueOf(kind.name), source)
            Kind.MINECRAFT_VERSION -> error("Use installMinecraft for versions")
        }
    }

    private fun resolveVersion(context: Context, requested: String): String? {
        if (!requested.equals(LATEST, true)) return requested
        val wait = CountDownLatch(1)
        val result = AtomicReference<String?>(null)
        MinecraftLatestVersionManager.refresh(context) { latest ->
            result.set(latest?.id?.takeIf { it.isNotBlank() })
            wait.countDown()
        }
        if (!wait.await(LATEST_TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
            return MinecraftLatestVersionManager.getCached(context)
        }
        return result.get() ?: MinecraftLatestVersionManager.getCached(context)
    }

    private fun submit(key: String, kind: Kind, listener: (TaskState) -> Unit, action: () -> Unit) {
        val queued = TaskState(key, kind, State.QUEUED, "Queued")
        if (active.putIfAbsent(key, queued) != null) return
        publish(queued, listener)
        executor.execute {
            android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND)
            publish(TaskState(key, kind, State.RUNNING, "Working"), listener)
            try {
                action()
                val finished = TaskState(key, kind, State.SUCCESS, "Completed")
                publish(finished, listener)
                scheduleStateCleanup(finished)
            } catch (t: Throwable) {
                val failed = TaskState(key, kind, State.FAILED, t.message ?: t.javaClass.simpleName)
                publish(failed, listener)
                scheduleStateCleanup(failed)
            }
        }
    }

    private fun publish(state: TaskState, listener: (TaskState) -> Unit) {
        active[state.key] = state
        mainHandler.post { listener(state) }
    }

    private fun scheduleStateCleanup(state: TaskState) {
        mainHandler.postDelayed({ active.remove(state.key, state) }, COMPLETED_STATE_RETENTION_MS)
    }
}
