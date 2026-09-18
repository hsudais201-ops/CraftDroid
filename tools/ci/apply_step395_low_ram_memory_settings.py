#!/usr/bin/env python3
"""Step 395: make saved launcher RAM settings conservative on low-memory devices."""
from pathlib import Path
import re, sys

FILES = {
    "settings": Path("app/src/main/java/com/example/settings/SettingsRepository.kt"),
    "screen": Path("app/src/main/java/com/example/ui/screens/SettingsScreen.kt"),
}

SETTINGS_METHOD = r'''
    fun getSafeRamMb(requestedMb: Int): Int {
        val total = getDeviceTotalRamMb().coerceAtLeast(768)
        val maxByDevice = when {
            total <= 1536 -> 768
            total <= 2048 -> 1024
            total <= 3072 -> 1280
            total <= 4096 -> 1536
            else -> minOf(2048, (total * 0.50f).toInt())
        }
        val minimum = 640
        return requestedMb.coerceIn(minimum, maxByDevice)
    }

    fun getRecommendedRamMb(): Int {
        val total = getDeviceTotalRamMb().coerceAtLeast(768)
        return when {
            total <= 1536 -> 640
            total <= 2048 -> 768
            total <= 3072 -> 1024
            total <= 4096 -> 1280
            else -> 1536
        }
    }
'''


def patch_settings(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    if "fun getSafeRamMb(" not in s:
        anchor = "    suspend fun updateSelectedVersion(versionId: String) {"
        if anchor not in s:
            raise SystemExit("[step395] SettingsRepository insertion anchor missing")
        s = s.replace(anchor, SETTINGS_METHOD + "\n" + anchor, 1)

    # Device-aware read path: old, excessively high saved values are clamped.
    old = '            ramMb = prefs[Keys.RAM_MB] ?: 2048,'
    new = '            ramMb = getSafeRamMb(prefs[Keys.RAM_MB] ?: getRecommendedRamMb()),'
    if old in s:
        s = s.replace(old, new, 1)

    old = '''    suspend fun updateRam(ramMb: Int) {
        context.dataStore.edit { it[Keys.RAM_MB] = ramMb }
    }'''
    new = '''    suspend fun updateRam(ramMb: Int) {
        context.dataStore.edit { it[Keys.RAM_MB] = getSafeRamMb(ramMb) }
    }'''
    if old in s:
        s = s.replace(old, new, 1)

    path.write_text(s, encoding="utf-8")


def patch_screen(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    old = '    val safeMaxRamMb = ((totalDeviceRamMb * 0.75f).toInt()).coerceAtLeast(1024)'
    new = '    val safeMaxRamMb = viewModel.container.settingsRepository.getSafeRamMb(Int.MAX_VALUE)'
    if old in s:
        s = s.replace(old, new, 1)
    # Avoid showing an impossible slider state when a previously saved value was too large.
    old = '    var ramSliderValue by remember(settings.ramMb) { mutableIntStateOf(settings.ramMb) }'
    new = '    var ramSliderValue by remember(settings.ramMb, safeMaxRamMb) { mutableIntStateOf(settings.ramMb.coerceIn(640, safeMaxRamMb)) }'
    if old in s:
        s = s.replace(old, new, 1)
    # 64-MB increments allow a conservative 640 MB recommendation on ~1 GB devices.
    s = s.replace('onValueChange = { ramSliderValue = (it / 128).toInt() * 128 }',
                  'onValueChange = { ramSliderValue = (it / 64).toInt() * 64 }', 1)
    s = re.sub(r'steps = \(\(safeMaxRamMb - 512\) / 128\)\.coerceAtLeast\(1\)',
               'steps = ((safeMaxRamMb - 640) / 64).coerceAtLeast(1)', s, count=1)
    path.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    settings = root / FILES["settings"]
    screen = root / FILES["screen"]
    if not settings.is_file() or not screen.is_file():
        raise SystemExit("[step395] required settings sources are missing")
    patch_settings(settings)
    patch_screen(screen)
    text = settings.read_text(encoding="utf-8")
    screen_text = screen.read_text(encoding="utf-8")
    for marker in ("fun getSafeRamMb(", "fun getRecommendedRamMb(", "getSafeRamMb(prefs[Keys.RAM_MB] ?: getRecommendedRamMb())"):
        if marker not in text:
            raise SystemExit("[step395] SettingsRepository contract missing: " + marker)
    for marker in ("getSafeRamMb(Int.MAX_VALUE)", "(it / 64).toInt() * 64"):
        if marker not in screen_text:
            raise SystemExit("[step395] SettingsScreen contract missing: " + marker)
    print("[step395] low-memory RAM defaults and persisted allocation limits hardened")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
