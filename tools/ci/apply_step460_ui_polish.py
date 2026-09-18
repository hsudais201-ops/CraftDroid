#!/usr/bin/env python3
"""Step 460: final visual identity and content-management UI polish."""
from pathlib import Path
import sys

UI_NAME = "DroidLauncherUiActivity.kt"
MARKER = "// STEP460_UI_POLISH"


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob(UI_NAME))
    if len(hits) != 1:
        raise SystemExit(f"[step460] expected exactly one {UI_NAME}, found {len(hits)}")
    return hits[0]


def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step460] missing method: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step460] missing opening brace: {signature}")
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ""
        n2 = source[i + 2] if i + 2 < len(source) else ""
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
    raise SystemExit(f"[step460] unterminated method: {signature}")


def insert_once(source: str, anchor: str, block: str, token: str) -> str:
    if token in source:
        return source
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit(f"[step460] insertion anchor missing: {anchor}")
    return source[:pos] + block + source[pos:]


HELPERS = r'''
    // STEP460_UI_POLISH

    private fun step460Surface(strokeAlpha: Int = 70): android.graphics.drawable.GradientDrawable =
        android.graphics.drawable.GradientDrawable().apply {
            cornerRadius = dp(16).toFloat()
            setColor(android.graphics.Color.argb(218, 10, 17, 28))
            setStroke(dp(1), android.graphics.Color.argb(strokeAlpha, 92, 244, 190))
        }

    private fun step460LogoBadge(labelText: String = "CD", size: Int = 46): TextView =
        TextView(this).apply {
            text = labelText
            textSize = if (labelText.length <= 2) 17f else 10f
            gravity = Gravity.CENTER
            setTextColor(android.graphics.Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.04f
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(14).toFloat()
                colors = intArrayOf(
                    android.graphics.Color.rgb(23, 205, 143),
                    android.graphics.Color.rgb(32, 120, 214)
                )
                orientation = android.graphics.drawable.GradientDrawable.Orientation.TL_BR
                setStroke(dp(1), android.graphics.Color.argb(150, 220, 255, 245))
            }
            elevation = dp(6).toFloat()
            contentDescription = "CraftDroid logo"
            minimumWidth = 0
            minimumHeight = 0
            layoutParams = LinearLayout.LayoutParams(dp(size), dp(size))
        }

    private fun step460MiniBadge(labelText: String): TextView =
        TextView(this).apply {
            text = labelText
            textSize = if (labelText.length <= 2) 15f else 10f
            gravity = Gravity.CENTER
            setTextColor(android.graphics.Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(12).toFloat()
                setColor(android.graphics.Color.argb(135, 29, 51, 66))
                setStroke(dp(1), android.graphics.Color.argb(110, 91, 233, 190))
            }
            elevation = dp(3).toFloat()
            minimumWidth = 0
            minimumHeight = 0
        }

    private fun step460Glyph(page: String): String = when (page) {
        "Home", "Game" -> "PLAY"
        "Instances" -> "INST"
        "Accounts", "Microsoft", "Offline" -> "ACC"
        "Content", "Downloads" -> "LIB"
        "Modpack" -> "PACK"
        "Mod" -> "MOD"
        "Shader Pack", "Shaders" -> "FX"
        "Resource Pack", "Resource Packs" -> "RES"
        "World", "Worlds" -> "WRLD"
        "Settings", "Renderer" -> "SET"
        "Java" -> "JAVA"
        "Controls" -> "CTRL"
        "Features" -> "FEAT"
        "Servers" -> "SRV"
        "FirstRun" -> "GO"
        else -> "CD"
    }

    private fun step460Subtitle(page: String): String = when (page) {
        "Home", "Game" -> "Ready to launch Minecraft Java Edition"
        "Instances" -> "Separate profiles, versions, loaders and content"
        "Accounts", "Microsoft", "Offline" -> "Manage sign-in and local profiles"
        "Content", "Downloads" -> "Mods, modpacks, shaders, resource packs and worlds"
        "Settings", "Renderer" -> "Performance, graphics, memory and display"
        "Java" -> "Automatic or per-version Java runtime selection"
        "Controls" -> "Customize every touch control for your device"
        "Features" -> "Launcher tools and advanced capabilities"
        "Servers" -> "Saved Minecraft server connections"
        else -> "CraftDroid launcher"
    }

    private fun step460PageBrand(page: String): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(9), dp(12), dp(9))
            background = step460Surface()
            addView(step460LogoBadge("CD", 46))
            val copy = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(10), 0, dp(8), 0)
                addView(step375Text(page, 19f, true))
                addView(step375Text(step460Subtitle(page), 11f).apply {
                    setTextColor(android.graphics.Color.argb(185, 215, 230, 240))
                })
            }
            addView(copy, LinearLayout.LayoutParams(0, dp(52), 1f))
            addView(step460MiniBadge(step460Glyph(page)), LinearLayout.LayoutParams(dp(58), dp(38)))
        }

    private fun step460CategoryCard(
        badge: String,
        titleText: String,
        detailText: String,
        action: () -> Unit
    ): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(8), dp(7), dp(10), dp(7))
            background = step460Surface(52)
            isClickable = true
            isFocusable = true
            contentDescription = titleText + " manager"
            elevation = dp(3).toFloat()
            setOnClickListener {
                animate().scaleX(0.97f).scaleY(0.97f).setDuration(55).withEndAction {
                    scaleX = 1f
                    scaleY = 1f
                    action()
                }.start()
            }
            addView(step460MiniBadge(badge), LinearLayout.LayoutParams(dp(48), dp(44)))
            val labels = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(9), 0, 0, 0)
                addView(step375Text(titleText, 13f, true))
                addView(step375Text(detailText, 10f).apply {
                    setTextColor(android.graphics.Color.argb(172, 210, 228, 236))
                })
            }
            addView(labels, LinearLayout.LayoutParams(dp(140), dp(56)))
        }

    private fun step460ContentCategoryRail(): android.widget.HorizontalScrollView =
        android.widget.HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            val row = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(step460CategoryCard("MOD", "Mods", "Install local content", { step460StartContent("Mod") }), LinearLayout.LayoutParams(dp(198), dp(74)).apply { marginEnd = dp(8) })
                addView(step460CategoryCard("PACK", "Modpacks", "Import .mrpack", { step460StartContent("Modpack") }), LinearLayout.LayoutParams(dp(198), dp(74)).apply { marginEnd = dp(8) })
                addView(step460CategoryCard("FX", "Shaders", "Shader packs", { step460StartContent("Shader Pack") }), LinearLayout.LayoutParams(dp(198), dp(74)).apply { marginEnd = dp(8) })
                addView(step460CategoryCard("RES", "Resource Packs", "Textures and UI", { step460StartContent("Resource Pack") }), LinearLayout.LayoutParams(dp(198), dp(74)).apply { marginEnd = dp(8) })
                addView(step460CategoryCard("WRLD", "Worlds", "Saved worlds", { step460StartContent("World") }), LinearLayout.LayoutParams(dp(198), dp(74)).apply { marginEnd = dp(8) })
                addView(step460CategoryCard("MC", "Versions", "Minecraft builds", { showPage("Content") }), LinearLayout.LayoutParams(dp(198), dp(74)))
            }
            addView(row)
        }

    private fun step460LoaderStrip(): android.widget.HorizontalScrollView =
        android.widget.HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            val row = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                listOf("V" to "Vanilla", "F" to "Fabric", "F" to "Forge", "N" to "NeoForge", "Q" to "Quilt").forEach { pair ->
                    addView(
                        step460CategoryCard(
                            pair.first,
                            pair.second,
                            "Loader",
                            {
                                android.widget.Toast.makeText(
                                    this@DroidLauncherUiActivity,
                                    pair.second + " selected for the current instance.",
                                    android.widget.Toast.LENGTH_SHORT
                                ).show()
                            }
                        ),
                        LinearLayout.LayoutParams(dp(154), dp(68)).apply { marginEnd = dp(7) }
                    )
                }
                addView(
                    step460CategoryCard("JAVA", "Java", "Runtime", { showPage("Java") }),
                    LinearLayout.LayoutParams(dp(154), dp(68))
                )
            }
            addView(row)
        }

    private fun step460HomeQuickActions(): android.widget.HorizontalScrollView =
        android.widget.HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            val row = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                listOf(
                    "MOD" to "Mods",
                    "PACK" to "Modpacks",
                    "FX" to "Shaders",
                    "RES" to "Resources",
                    "WRLD" to "Worlds"
                ).forEach { pair ->
                    addView(
                        step460CategoryCard(pair.first, pair.second, "Open manager", { showPage("Content") }),
                        LinearLayout.LayoutParams(dp(176), dp(72)).apply { marginEnd = dp(8) }
                    )
                }
            }
            addView(row)
        }

    private fun step460StartContent(type: String) {
        when (type) {
            "Modpack", "Mod", "Shader Pack", "Resource Pack", "World" -> step391StartContentImport(type)
            else -> showPage("Content")
        }
    }
'''


def add_helpers(source: str) -> str:
    return insert_once(source, "    override fun onCreate(", HELPERS + "\n", MARKER)


def add_after_title(block: str, title_prefix: str, insertion: str) -> str:
    if insertion.strip() in block:
        return block
    pos = block.find(title_prefix)
    if pos < 0:
        raise SystemExit("[step460] page title anchor missing: " + title_prefix)
    line_end = block.find("\n", pos)
    if line_end < 0:
        raise SystemExit("[step460] malformed page title line: " + title_prefix)
    return block[:line_end] + insertion + block[line_end:]


def patch_show_page(source: str) -> str:
    start, end = method_span(source, "    private fun showPage(page: String)")
    block = source[start:end]
    if "step460PageBrand(page)" not in block:
        anchor = "        pageArea.removeAllViews()"
        if anchor not in block:
            raise SystemExit("[step460] showPage reset anchor missing")
        block = block.replace(
            anchor,
            anchor + '\n        pageArea.addView(step460PageBrand(page), LinearLayout.LayoutParams(-1, dp(76)).apply { bottomMargin = dp(8) })',
            1,
        )
    return source[:start] + block + source[end:]


def patch_content(source: str) -> str:
    start, end = method_span(source, "    private fun step375Content()")
    block = source[start:end]
    block = add_after_title(
        block,
        '        pageArea.addView(step375Title("Downloads"',
        '\n        pageArea.addView(step460ContentCategoryRail(), LinearLayout.LayoutParams(-1, dp(82)).apply { bottomMargin = dp(8) })'
        '\n        pageArea.addView(step460LoaderStrip(), LinearLayout.LayoutParams(-1, dp(76)).apply { bottomMargin = dp(7) })',
    )
    block = block.replace(
        'row.addView(step375Text("▣", 22f, true), LinearLayout.LayoutParams(dp(40), dp(52)))',
        'row.addView(step460MiniBadge("MC"), LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginEnd = dp(7) })',
        1,
    )
    return source[:start] + block + source[end:]


def patch_home(source: str) -> str:
    start, end = method_span(source, "    private fun step375Home()")
    block = source[start:end]
    block = add_after_title(
        block,
        '        pageArea.addView(step375Title("Home"',
        '\n        pageArea.addView(step460HomeQuickActions(), LinearLayout.LayoutParams(-1, dp(80)).apply { bottomMargin = dp(8) })'
        '\n        pageArea.addView(step460LoaderStrip(), LinearLayout.LayoutParams(-1, dp(76)).apply { bottomMargin = dp(8) })',
    )
    return source[:start] + block + source[end:]


def patch_instances(source: str) -> str:
    start, end = method_span(source, "    private fun step375Instances()")
    block = source[start:end]
    anchor = 'val r = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }'
    if 'step460MiniBadge("I")' not in block:
        if anchor not in block:
            raise SystemExit("[step460] instance row anchor missing")
        block = block.replace(
            anchor,
            anchor + '\n            r.addView(step460MiniBadge("I"), LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginEnd = dp(8) })',
            1,
        )
    return source[:start] + block + source[end:]


def patch_settings(source: str) -> str:
    start, end = method_span(source, "    private fun step375Settings()")
    block = source[start:end]
    block = add_after_title(
        block,
        '        pageArea.addView(step375Title("Settings"',
        '\n        pageArea.addView(step460LoaderStrip(), LinearLayout.LayoutParams(-1, dp(76)).apply { bottomMargin = dp(8) })',
    )
    return source[:start] + block + source[end:]


def patch_java(source: str) -> str:
    start, end = method_span(source, "    private fun javaPage()")
    block = source[start:end]
    if 'step460MiniBadge("J")' not in block:
        brace = block.find("{")
        line_end = block.find("\n", brace)
        if line_end < 0:
            raise SystemExit("[step460] javaPage malformed")
        insertion = (
            '\n        val runtimeHeader = LinearLayout(this).apply {'
            '\n            orientation = LinearLayout.HORIZONTAL'
            '\n            gravity = Gravity.CENTER_VERTICAL'
            '\n            addView(step460MiniBadge("J"), LinearLayout.LayoutParams(dp(42), dp(42)).apply { marginEnd = dp(9) })'
            '\n            addView(step375Text("AUTO RUNTIME", 14f, true))'
            '\n        }'
            '\n        pageArea.addView(runtimeHeader, LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(6) })'
        )
        block = block[:line_end] + insertion + block[line_end:]
    return source[:start] + block + source[end:]


def validate(source: str) -> None:
    required = (
        MARKER,
        'step460LogoBadge("CD", 46)',
        "private fun step460PageBrand(page: String)",
        "private fun step460ContentCategoryRail()",
        "private fun step460LoaderStrip()",
        "private fun step460HomeQuickActions()",
        "private fun step460StartContent(type: String)",
        'step460StartContent("Mod")',
        'step460StartContent("Modpack")',
        'step460StartContent("Shader Pack")',
        'step460StartContent("Resource Pack")',
        'step460StartContent("World")',
        "step460PageBrand(page)",
        "step460LoaderStrip()",
        'step391StartContentImport("Mod")',
        'step391StartContentImport("Modpack")',
        'step391StartContentImport("Shader Pack")',
        'step391StartContentImport("Resource Pack")',
        'step391StartContentImport("World")',
    )
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit("[step460] missing contract(s): " + ", ".join(missing))
    for label in ("Mods", "Modpacks", "Shaders", "Resource Packs", "Worlds", "Fabric", "Forge", "NeoForge", "Quilt", "Java"):
        if label not in source:
            raise SystemExit("[step460] missing visible label: " + label)
    for sig in (
        "private fun step460StartContent(type: String)",
        "private fun step460PageBrand(page: String)",
        "private fun step460ContentCategoryRail()",
        "private fun step460LoaderStrip()",
        "private fun step460HomeQuickActions()",
    ):
        if source.count(sig) != 1:
            raise SystemExit("[step460] declaration count for " + sig + " is " + str(source.count(sig)))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")

    if MARKER not in source:
        source = add_helpers(source)

    source = patch_show_page(source)
    source = patch_content(source)
    source = patch_home(source)
    source = patch_instances(source)
    source = patch_settings(source)
    source = patch_java(source)

    validate(source)
    ui.write_text(source, encoding="utf-8")
    print("[step460] final branded UI and requested Mods/Modpacks/Shaders/Resource Packs/Worlds categories applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
