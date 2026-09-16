#!/usr/bin/env python3
"""Step 340: final, idempotent Settings/Renderer repair after all UI rewrites."""
from pathlib import Path
import re, sys

MARKER = "// STEP340_SETTINGS_REFERENCE_POLISH"
SELECTED = "val step340SelectedSettingsColor = Color.rgb(231, 240, 249)"

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step340] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Repairs from earlier reference generators are intentionally normalized here.
    s = s.replace("val spacer = Space(this)", "val spacer = android.widget.Space(this)")
    s = s.replace('Enable fullscreen mode, ignoring safe areas like notches end punch-holes.', 'Enable fullscreen mode, ignoring safe areas like notches and punch-holes.')
    s = re.sub(r'(\n\s*// STEP340_SETTINGS_REFERENCE_POLISH\n\s*// Selected Settings/Renderer reference style contract\.\n\s*)+' , '\n        ' + MARKER + '\n        // Selected Settings/Renderer reference style contract.\n        ', s)
    # Keep only one selected-style declaration per rendererPage method.
    def clean_renderer(m: re.Match) -> str:
        block = m.group(0)
        block = re.sub(r'(?m)^\s*// STEP340_SETTINGS_REFERENCE_POLISH\n', '', block)
        block = re.sub(r'(?m)^\s*val step340SelectedSettingsColor = Color\.rgb\(231, 240, 249\)\s*\n?', '', block)
        return '    private fun rendererPage() {\n        ' + MARKER + '\n        // Selected Settings/Renderer reference style contract.\n        ' + SELECTED + '\n' + block.split('\n', 1)[1]
    match = re.search(r'    private fun rendererPage\(\) \{[\s\S]*?\n    \}\n\n    private fun javaPage\(\)', s)
    if match:
        renderer = match.group(0)
        renderer_body = renderer[len('    private fun rendererPage() {\n'):]
        # Remove duplicate declarations/comments only; preserve functional UI.
        renderer_body = re.sub(r'(?m)^\s*// STEP340_SETTINGS_REFERENCE_POLISH\s*\n', '', renderer_body)
        renderer_body = re.sub(r'(?m)^\s*// Selected Settings/Renderer reference style contract\.\s*\n', '', renderer_body)
        renderer_body = re.sub(r'(?m)^\s*val step340SelectedSettingsColor = Color\.rgb\(231, 240, 249\)\s*\n', '', renderer_body)
        renderer_body = renderer_body.replace('"The global default renderer uses a dynamic library translation layer to ensure runs\nsmoothly on mobile devices"', '"The global default renderer uses a dynamic library translation layer to ensure runs\\nsmoothly on mobile devices"')
        renderer_body = renderer_body.replace('"The global default renderer uses a dynamic library translation layer to ensure runs\n', '"The global default renderer uses a dynamic library translation layer to ensure runs\\n')
        # Recover a malformed two-line Kotlin string if earlier generator emitted a physical newline.
        renderer_body = re.sub(r'"The global default renderer uses a dynamic library translation layer to ensure runs\s*\n\s*smoothly on mobile devices"', '"The global default renderer uses a dynamic library translation layer to ensure runs\\nsmoothly on mobile devices"', renderer_body)
        prefix = '    private fun rendererPage() {\n        ' + MARKER + '\n        // Selected Settings/Renderer reference style contract.\n        ' + SELECTED + '\n'
        s = s[:match.start()] + prefix + renderer_body + s[match.end():]

    # Repair the common Step344 malformed joinToString emitted as a physical newline.
    s = re.sub(r'names\.joinToString\("\s*\n\s*"\)', 'names.joinToString("\\n")', s)
    # Ensure a sane renderer helper remains present even when a late method rewrite deleted it.
    if 'private fun addReferenceSetting(card: LinearLayout, name: String, description: String,' not in s:
        # Step339 normally supplies this. Do not invent a second copy here; fail clearly so the upstream generator can be fixed.
        raise SystemExit('[step340] addReferenceSetting helper missing after final UI generation')

    ui.write_text(s, encoding="utf-8")
    print('[step340] Settings/Renderer style, duplicate declarations, and escaped-string syntax normalized')
    return 0

if __name__ == '__main__': raise SystemExit(main())
