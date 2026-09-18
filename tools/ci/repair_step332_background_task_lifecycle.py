#!/usr/bin/env python3
"""Step 332: allow completed background install keys to be retried safely."""
from pathlib import Path
import sys


def one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step332] expected exactly one {name}, found {len(hits)}")
    return hits[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = one(root / "app/src/main/java", "LauncherBackgroundInstallController.kt")
    s = path.read_text(encoding="utf-8")

    # Step 400+ already provides a bounded lifecycle with active-state expiry.
    # Preserve it instead of adding the old unbounded lastStates map.
    modern_contract = (
        "COMPLETED_STATE_RETENTION_MS" in s
        and "scheduleStateCleanup(state: TaskState)" in s
        and "active.remove(state.key, state)" in s
    )
    if modern_contract:
        for marker in (
            "private val active = ConcurrentHashMap<String, TaskState>()",
            "Executors.newSingleThreadExecutor",
            "COMPLETED_STATE_RETENTION_MS",
            "private fun scheduleStateCleanup(state: TaskState)",
        ):
            if marker not in s:
                raise SystemExit("[step332] modern lifecycle marker missing: " + marker)
        print("[step332] bounded modern lifecycle already installed; legacy lastStates map not applied")
        return 0

    if "private val lastStates = ConcurrentHashMap<String, TaskState>()" not in s:
        anchor = "    private val active = ConcurrentHashMap<String, TaskState>()\n"
        if anchor not in s:
            raise SystemExit("[step332] active map anchor missing")
        s = s.replace(anchor, anchor + "    private val lastStates = ConcurrentHashMap<String, TaskState>()\n", 1)

    s = s.replace("    fun state(key: String): TaskState? = active[key]", "    fun state(key: String): TaskState? = active[key] ?: lastStates[key]", 1)

    old = '''        executor.execute {
            publish(TaskState(key, kind, State.RUNNING, "Working"), listener)
            try {
                action()
                publish(TaskState(key, kind, State.SUCCESS, "Completed"), listener)
            } catch (t: Throwable) {
                publish(TaskState(key, kind, State.FAILED, t.message ?: t.javaClass.simpleName), listener)
            }
        }
'''
    new = '''        executor.execute {
            publish(TaskState(key, kind, State.RUNNING, "Working"), listener)
            try {
                action()
                val complete = TaskState(key, kind, State.SUCCESS, "Completed")
                publish(complete, listener)
                lastStates[key] = complete
            } catch (t: Throwable) {
                val failed = TaskState(key, kind, State.FAILED, t.message ?: t.javaClass.simpleName)
                publish(failed, listener)
                lastStates[key] = failed
            } finally {
                active.remove(key)
            }
        }
'''
    if old not in s:
        raise SystemExit("[step332] task lifecycle block missing")
    s = s.replace(old, new, 1)

    if "active.remove(key)" not in s or "lastStates[key] = complete" not in s:
        raise SystemExit("[step332] lifecycle hardening did not apply")
    path.write_text(s, encoding="utf-8")
    print("[step332] completed/failed background tasks no longer permanently block retries")
    print("[step332] last task state remains queryable after active task cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
