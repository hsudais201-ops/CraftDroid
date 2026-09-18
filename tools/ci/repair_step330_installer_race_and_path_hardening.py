#!/usr/bin/env python3
"""Step 330: eliminate installer races and unsafe Minecraft version path inputs."""
from pathlib import Path
import sys


def one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step330] expected exactly one {name}, found {len(hits)}")
    return hits[0]


def patch_installer(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = path.read_text(encoding="utf-8")

    if "private val inFlight = ConcurrentHashMap.newKeySet<String>()" not in s:
        import_anchor = "import java.util.concurrent.Executors\n"
        if import_anchor not in s:
            raise SystemExit("[step330] Executors import anchor missing")
        if "import java.util.concurrent.ConcurrentHashMap" not in s:
            s = s.replace(import_anchor, import_anchor + "import java.util.concurrent.ConcurrentHashMap\n", 1)
        anchors = (
            "    private val executor = Executors.newCachedThreadPool()\n",
            "    private val executor = Executors.newSingleThreadExecutor { runnable ->",
        )
        anchor = next((item for item in anchors if item in s), None)
        if anchor is None:
            raise SystemExit("[step330] executor anchor missing")
        if anchor.endswith("()\n"):
            s = s.replace(anchor, anchor + "    private val inFlight = ConcurrentHashMap.newKeySet<String>()\n", 1)
        else:
            handler_anchor = "    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n"
            if handler_anchor not in s:
                handler_anchor = "    private val mainHandler = Handler(Looper.getMainLooper())\n"
            if handler_anchor not in s:
                raise SystemExit("[step330] hardened executor insertion anchor missing")
            s = s.replace(handler_anchor, handler_anchor + "    private val inFlight = ConcurrentHashMap.newKeySet<String>()\n", 1)

    marker = "        if (version.isBlank()) {\n"
    guard = '''        val safeVersion = version.trim()
        if (!safeVersion.matches(Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"))) {
            listener?.onError(version, IllegalArgumentException("Invalid Minecraft version id"))
            return
        }
'''
    if "Invalid Minecraft version id" not in s:
        if marker not in s:
            raise SystemExit("[step330] install validation anchor missing")
        s = s.replace(marker, guard + marker, 1)

    if "if (!inFlight.add(safeVersion)) return" not in s:
        legacy_marker = "        if (isInstalled(context, version)) {\n            listener?.onComplete(version)\n            return\n        }\n"
        modern_marker = "        if (isInstalled(context, safeVersion)) {\n            listener?.onComplete(safeVersion)\n            return\n        }\n"
        marker = legacy_marker if legacy_marker in s else modern_marker if modern_marker in s else None
        if marker is None:
            raise SystemExit("[step330] install preflight anchor missing for legacy or hardened installer")
        s = s.replace(marker, marker + "        if (!inFlight.add(safeVersion)) return\n", 1)

        modern_catch = """            } catch (t: Throwable) {
                setState(context, safeVersion, State.FAILED, t.message ?: t.javaClass.simpleName)
                listener?.onError(safeVersion, t)
            }
        }
"""
        legacy_catch = """            } catch (t: Throwable) {
                setState(context, version, State.FAILED, t.message ?: t.javaClass.simpleName)
                listener?.onError(version, t)
            }
        """
        if modern_catch in s:
            s = s.replace(
                modern_catch,
                """            } catch (t: Throwable) {
                setState(context, safeVersion, State.FAILED, t.message ?: t.javaClass.simpleName)
                listener?.onError(safeVersion, t)
            } finally {
                inFlight.remove(safeVersion)
            }
        }
""",
                1,
            )
        elif legacy_catch in s:
            s = s.replace(
                legacy_catch,
                """            } catch (t: Throwable) {
                setState(context, version, State.FAILED, t.message ?: t.javaClass.simpleName)
                listener?.onError(version, t)
            } finally {
                inFlight.remove(safeVersion)
            }
        """,
                1,
            )
        else:
            raise SystemExit("[step330] install catch/finally anchor missing")

    s = s.replace("        if (isInstalled(context, version)) {", "        if (isInstalled(context, safeVersion)) {", 1)
    s = s.replace("listener?.onComplete(version)\n            return\n        }\n        if (!inFlight.add(safeVersion)", "listener?.onComplete(safeVersion)\n            return\n        }\n        if (!inFlight.add(safeVersion)", 1)
    s = s.replace("            try {\n                setState(context, version, State.DOWNLOADING, null)\n                installInternal(context, version, listener)", "            try {\n                setState(context, safeVersion, State.DOWNLOADING, null)\n                installInternal(context, safeVersion, listener)", 1)
    s = s.replace("                setState(context, version, State.INSTALLED, null)\n                listener?.onComplete(version)", "                setState(context, safeVersion, State.INSTALLED, null)\n                listener?.onComplete(safeVersion)", 1)
    s = s.replace("                setState(context, version, State.FAILED, t.message ?: t.javaClass.simpleName)\n                listener?.onError(version, t)", "                setState(context, safeVersion, State.FAILED, t.message ?: t.javaClass.simpleName)\n                listener?.onError(safeVersion, t)", 1)

    path.write_text(s, encoding="utf-8")


def verify(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = path.read_text(encoding="utf-8")
    required = (
        "private val inFlight = ConcurrentHashMap.newKeySet<String>()",
        "Invalid Minecraft version id",
        "if (!inFlight.add(safeVersion)) return",
        "inFlight.remove(safeVersion)",
    )
    for needle in required:
        if needle not in s:
            raise SystemExit(f"[step330] missing hardened installer contract: {needle}")
    if s.count("fun install(context: Context, version: String") != 1:
        raise SystemExit("[step330] duplicate install declaration detected")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    patch_installer(root)
    verify(root)
    print("[step330] installer rejects unsafe version IDs before filesystem access")
    print("[step330] duplicate concurrent installs are deduplicated and always released")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
