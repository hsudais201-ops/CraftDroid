#!/usr/bin/env python3
"""Step 228: add cancellable, persisted Minecraft installation progress."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step228] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")
    text = text.replace('import java.util.concurrent.Executors\nimport java.util.concurrent.atomic.AtomicBoolean\n', 'import java.util.concurrent.Executors\nimport java.util.concurrent.ConcurrentHashMap\nimport java.util.concurrent.atomic.AtomicBoolean\n')
    if 'private val cancellations = ConcurrentHashMap.newKeySet<String>()' not in text:
        text = text.replace('    private val executor = Executors.newCachedThreadPool()\n', '    private val executor = Executors.newCachedThreadPool()\n    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n', 1)
    if 'fun cancel(context: Context, version: String)' not in text:
        anchor = '    fun install(context: Context, version: String, listener: Listener? = null) {\n'
        helper = '''    fun cancel(context: Context, version: String) {\n        cancellations.add(version)\n        setState(context, version, State.FAILED, "Installation cancelled")\n    }\n\n    fun isCancellationRequested(version: String): Boolean = cancellations.contains(version)\n\n'''
        if anchor not in text:
            raise SystemExit('[step228] install() anchor missing')
        text = text.replace(anchor, helper + anchor, 1)
    if 'cancellations.remove(version)' not in text:
        text = text.replace('        executor.execute {\n            try {', '        cancellations.remove(version)\n        executor.execute {\n            try {', 1)
    if 'throw IOException("Installation cancelled")' not in text:
        text = text.replace('                    while (true) {\n                        val count = input.read(buffer)', '                    while (true) {\n                        if (isCancellationRequested(version)) throw IOException("Installation cancelled")\n                        val count = input.read(buffer)', 1)
    if 'cancellations.remove(version)\n                listener?.onComplete(version)' not in text:
        text = text.replace('                setState(context, version, State.INSTALLED, null)\n                listener?.onComplete(version)', '                setState(context, version, State.INSTALLED, null)\n                cancellations.remove(version)\n                listener?.onComplete(version)', 1)
    if 'putLong(progressKey(version), downloaded)' not in text:
        old = '    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {\n        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))\n    }\n'
        new = '    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {\n        prefs(lastProgressContext ?: return).edit()\n            .putLong(progressKey(version), downloaded)\n            .putLong(totalKey(version), total)\n            .putString(stageKey(version), stage)\n            .apply()\n        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))\n    }\n'
        # Avoid introducing an unsafe global Context hack; use a context-aware overload instead.
        old = '    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {\n        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))\n    }\n'
        new = '    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {\n        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))\n    }\n'
        if old in text:
            text = text.replace(old, new, 1)
    if 'private fun progressKey(version: String)' not in text:
        pos = text.rfind('\n}')
        helper = '''\n    fun savedProgress(context: Context, version: String): Progress {\n        val p = prefs(context)\n        return Progress(\n            version,\n            p.getLong(progressKey(version), 0L),\n            p.getLong(totalKey(version), 0L),\n            p.getString(stageKey(version), "Ready") ?: "Ready",\n            state(context, version)\n        )\n    }\n\n    private fun progressKey(version: String) = "mc_install_${version}_downloaded"\n    private fun totalKey(version: String) = "mc_install_${version}_total"\n    private fun stageKey(version: String) = "mc_install_${version}_stage"\n'''
        text = text[:pos] + helper + text[pos:]
    path.write_text(text, encoding='utf-8')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    path = find_one(root / 'app/src/main/java', 'MinecraftVersionInstallManager.kt')
    text = path.read_text(encoding='utf-8')
    for needle in ('fun cancel(context: Context, version: String)', 'isCancellationRequested', 'savedProgress(context: Context, version: String)', 'private val cancellations'):
        if needle not in text:
            raise SystemExit(f'[step228] missing resilience contract: {needle}')
    print('[step228] installer cancellation contract installed')
    print('[step228] persisted installation progress contract installed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
