#!/usr/bin/env python3
"""Step 228: add cancellable, persisted Minecraft installation progress."""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step228] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    if "import java.util.concurrent.ConcurrentHashMap" not in text:
        marker = "import java.util.concurrent.Executors\n"
        if marker not in text:
            raise SystemExit("[step228] executor import anchor missing")
        text = text.replace(marker, marker + "import java.util.concurrent.ConcurrentHashMap\n", 1)

    if "private val cancellations = ConcurrentHashMap.newKeySet<String>()" not in text:
        marker = "    private val executor = Executors.newCachedThreadPool()\n"
        if marker not in text:
            raise SystemExit("[step228] executor declaration anchor missing")
        text = text.replace(
            marker,
            marker + "    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n",
            1,
        )

    if "fun cancel(context: Context, version: String)" not in text:
        match = re.search(r"^    fun install\(context: Context, version: String[^\n]*\) \{", text, re.MULTILINE)
        if not match:
            raise SystemExit("[step228] install(context, version) anchor missing")
        helper = '''    fun cancel(context: Context, version: String) {\n        cancellations.add(version)\n        setState(context, version, State.FAILED, "Installation cancelled")\n    }\n\n    fun isCancellationRequested(version: String): Boolean =\n        cancellations.contains(version)\n\n'''
        text = text[:match.start()] + helper + text[match.start():]

    # Clear a stale cancellation request whenever a new installation starts.
    if "cancellations.remove(version)\n        executor.execute" not in text:
        marker = "        executor.execute {\n            try {"
        if marker not in text:
            raise SystemExit("[step228] install executor anchor missing")
        text = text.replace(
            marker,
            "        cancellations.remove(version)\n        executor.execute {\n            try {",
            1,
        )

    # Persist a cancelled state without allowing the installer to continue downloading.
    if "Installation cancelled" not in text[text.find("private fun downloadResumable"):]:
        marker = "                    while (true) {\n                        val count = input.read(buffer)"
        if marker in text:
            text = text.replace(
                marker,
                "                    while (true) {\n                        if (isCancellationRequested(version)) {\n                            throw IOException(\"Installation cancelled\")\n                        }\n                        val count = input.read(buffer)",
                1,
            )
        else:
            raise SystemExit("[step228] download loop anchor missing")

    if "cancellations.remove(version)\n                listener?.onComplete(version)" not in text:
        marker = "                setState(context, version, State.INSTALLED, null)\n                listener?.onComplete(version)"
        if marker not in text:
            raise SystemExit("[step228] install completion anchor missing")
        text = text.replace(
            marker,
            "                setState(context, version, State.INSTALLED, null)\n                cancellations.remove(version)\n                listener?.onComplete(version)",
            1,
        )

    if "private fun progressKey(version: String)" not in text:
        pos = text.rfind("\n}")
        if pos < 0:
            raise SystemExit("[step228] object closing brace not found")
        helper = '''\n    fun savedProgress(context: Context, version: String): Progress {\n        val p = prefs(context)\n        return Progress(\n            version,\n            p.getLong(progressKey(version), 0L),\n            p.getLong(totalKey(version), 0L),\n            p.getString(stageKey(version), "Ready") ?: "Ready",\n            state(context, version)\n        )\n    }\n\n    private fun progressKey(version: String) = "mc_install_${version}_downloaded"\n    private fun totalKey(version: String) = "mc_install_${version}_total"\n    private fun stageKey(version: String) = "mc_install_${version}_stage"\n'''
        text = text[:pos] + helper + text[pos:]

    path.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    patch_installer(root)
    text = path.read_text(encoding="utf-8")
    for needle in (
        "fun cancel(context: Context, version: String)",
        "isCancellationRequested",
        "savedProgress(context: Context, version: String)",
        "private val cancellations",
    ):
        if needle not in text:
            raise SystemExit(f"[step228] missing resilience contract: {needle}")
    print("[step228] installer cancellation contract installed")
    print("[step228] persisted installation progress contract installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
