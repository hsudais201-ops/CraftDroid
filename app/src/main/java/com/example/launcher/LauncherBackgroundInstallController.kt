package com.example.launcher

import android.content.Context
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * Background controller for installs/imports.
 * At most one task runs for a logical key; Minecraft installs wait for the
 * underlying asynchronous installer to report completion before succeeding.
 */
object LauncherBackgroundInstallController {
    enum class Kind { MINECRAFT_VERSION, MODPACK, MOD, SHADER, RESOURCE_PACK, WORLD }
    enum class State { QUEUED, RUNNING, SUCCESS, FAILED }
    data class TaskState(val key: String, val kind: Kind, val state: State, val message: String)

    private val executor = Executors.newFixedThreadPool(2)
    private val active = ConcurrentHashMap<String, TaskState>()

    fun state(key: String): TaskState? = active[key]

    fun installMinecraft(context: Context, version: String, listener: (TaskState) -> Unit = {}) {
        val key = "minecraft:$version"
        submit(key, Kind.MINECRAFT_VERSION, listener) {
            val done = CountDownLatch(1)
            val failure = AtomicReference<Throwable?>(null)
            MinecraftVersionInstallManager.install(context, version, object : MinecraftVersionInstallManager.Listener {
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
        val key = "${kind.name.lowercase()}:${source.absolutePath}"
        submit(key, kind, listener) {
            when (kind) {
                Kind.MODPACK, Kind.WORLD -> MinecraftContentManager.importArchive(context, MinecraftContentManager.Kind.valueOf(kind.name), source)
                Kind.MOD, Kind.SHADER, Kind.RESOURCE_PACK -> MinecraftContentManager.importFile(context, MinecraftContentManager.Kind.valueOf(kind.name), source)
                Kind.MINECRAFT_VERSION -> error("Use installMinecraft for versions")
            }
        }
    }

    private fun submit(key: String, kind: Kind, listener: (TaskState) -> Unit, action: () -> Unit) {
        val queued = TaskState(key, kind, State.QUEUED, "Queued")
        if (active.putIfAbsent(key, queued) != null) return
        listener(queued)
        executor.execute {
            publish(TaskState(key, kind, State.RUNNING, "Working"), listener)
            try {
                action()
                publish(TaskState(key, kind, State.SUCCESS, "Completed"), listener)
            } catch (t: Throwable) {
                publish(TaskState(key, kind, State.FAILED, t.message ?: t.javaClass.simpleName), listener)
            }
        }
    }

    private fun publish(state: TaskState, listener: (TaskState) -> Unit) {
        active[state.key] = state
        listener(state)
    }
}
