#!/usr/bin/env python3
"""Step 460 verification for the final generated launcher UI."""
from pathlib import Path
import sys

UI_NAME = "DroidLauncherUiActivity.kt"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    hits = list((root / "app/src/main/java").rglob(UI_NAME))
    if len(hits) != 1:
        raise SystemExit(f"[step460-verify] expected one {UI_NAME}, found {len(hits)}")
    s = hits[0].read_text(encoding="utf-8")
    required = (
        "// STEP460_UI_POLISH",
        'step460LogoBadge("CD", 46)',
        "step460PageBrand(page)",
        "step460ContentCategoryRail()",
        "step460LoaderStrip()",
        "step460HomeQuickActions()",
        "private fun step460StartContent(type: String)",
        'step391StartContentImport("Mod")',
        'step391StartContentImport("Modpack")',
        'step391StartContentImport("Shader Pack")',
        'step391StartContentImport("Resource Pack")',
        'step391StartContentImport("World")',
        "Mods",
        "Modpacks",
        "Shaders",
        "Resource Packs",
        "Worlds",
        "Fabric",
        "Forge",
        "NeoForge",
        "Quilt",
        "Java",
    )
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit("[step460-verify] missing: " + ", ".join(missing))
    for sig in (
        "private fun step460PageBrand(page: String)",
        "private fun step460ContentCategoryRail()",
        "private fun step460LoaderStrip()",
        "private fun step460HomeQuickActions()",
        "private fun step460StartContent(type: String)",
    ):
        if s.count(sig) != 1:
            raise SystemExit("[step460-verify] wrong declaration count: " + sig)
    reset = s.find("pageArea.removeAllViews()")
    brand = s.find("pageArea.addView(step460PageBrand(page)")
    if reset < 0 or brand < 0 or brand < reset:
        raise SystemExit("[step460-verify] page brand is not inserted at the final render boundary")
    helper_start = s.find("// STEP460_UI_POLISH")
    helper_end = s.find("    private fun step460StartContent(type: String)", helper_start)
    if helper_start < 0 or helper_end < 0:
        raise SystemExit("[step460-verify] unable to isolate Step460 helper boundary")
    helper_text = s[helper_start:helper_end]
    for forbidden in ("HttpURLConnection", "URL(", "BitmapFactory.decodeStream"):
        if forbidden in helper_text:
            raise SystemExit("[step460-verify] network image loading found in Step460 helper code: " + forbidden)
    print("[step460-verify] final UI branding, category cards, loaders and real import bridges pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
