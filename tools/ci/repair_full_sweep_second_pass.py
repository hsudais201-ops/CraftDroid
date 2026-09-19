#!/usr/bin/env python3
"""Second-pass live fixes after the full sweep's first compile."""
from pathlib import Path
import re
import sys

MARKER="// STEP_FULL_SWEEP_SECOND_PASS"

def patch(root, rel, fn):
    p=root/rel
    if not p.is_file():
        raise SystemExit("[second-pass] missing "+rel)
    p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

def method_span(src, sig):
    a=src.find(sig)
    if a<0: raise SystemExit("[second-pass] missing "+sig)
    b0=src.find("{",a)
    if b0<0: raise SystemExit("[second-pass] missing brace")
    d=0; state="code"; quote=False; esc=False; triple=False; i=b0
    while i<len(src):
        c=src[i]; n=src[i+1] if i+1<len(src) else ""; n2=src[i+2] if i+2<len(src) else ""
        if triple:
            if c=='"' and n=='"' and n2=='"': triple=False; i+=3
            else: i+=1
            continue
        if quote:
            if esc: esc=False
            elif c=="\\": esc=True
            elif c=='"': quote=False
            i+=1; continue
        if c=='"' and n=='"' and n2=='"': triple=True; i+=3; continue
        if c=='"': quote=True; i+=1; continue
        if c=='/' and n=='/':
            j=src.find("\n",i); i=len(src) if j<0 else j+1; continue
        if c=='{' : d+=1
        elif c=='}':
            d-=1
            if d==0: return a,i+1
        i+=1
    raise SystemExit("[second-pass] unterminated "+sig)

def replace_method(src,sig,repl):
    a,b=method_span(src,sig)
    return src[:a]+repl+src[b:]

def patch_home(root):
    rel="app/src/main/java/com/example/ui/screens/HomeScreen.kt"
    def f(s):
        s=s.replace('IconButton(onClick = { utilityDialog = "Notifications" }, modifier = Modifier.testTag("notifications_button")) {',
                    'IconButton(onClick = { viewModel.navigateTo(LauncherScreen.LOGS) }, modifier = Modifier.testTag("logs_button")) {',1)
        s=s.replace('Icon(Icons.Default.Info, "Notifications")','Icon(Icons.Default.Info, "Logs")',1)
        s=s.replace('                        NotificationBadge(2)\n','',1)
        s=s.replace('var utilityDialog by remember { mutableStateOf<String?>(null) }\n','',1)
        # Remove the entire fake Store/Events/Leaderboard quick-access dialog block if still present.
        s=re.sub(r'\n\s*utilityDialog\?\.let \{ name ->[\\s\\S]*?\n\s*\}\n\s*\n\s*\}', '\n        }\n', s, count=1)
        # Remove the synthetic resource/currency surface even if late generators
        # change whitespace/comments. Locate the real Surface( call enclosing
        # the hardcoded values, then delete that balanced Compose call.
        needle='ResourcePill("●", "1,250"'
        hit=s.find(needle)
        if hit >= 0:
            surface=s.rfind("Surface(", 0, hit)
            if surface < 0:
                raise SystemExit("[second-pass] fake resource values found but enclosing Surface() is missing")
            depth=0
            quote=False
            escaped=False
            i=surface
            while i < len(s):
                c=s[i]
                if quote:
                    if escaped:
                        escaped=False
                    elif c == "\\\\":
                        escaped=True
                    elif c == '"':
                        quote=False
                    i += 1
                    continue
                if c == '"':
                    quote=True
                    i += 1
                    continue
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        line_start=s.rfind("\\n",0,surface)+1
                        line_end=s.find("\\n",i)
                        if line_end < 0:
                            line_end=len(s)
                        else:
                            line_end += 1
                        s=s[:line_start]+s[line_end:]
                        break
                i += 1
        return s
    patch(root,rel,f)

def patch_main_activity(root):
    rel="app/src/main/java/com/example/MainActivity.kt"
    def f(s):
        # GameActivity/GameSurfaceView owns game input. MainActivity must not swallow
        # W/A/S/D/etc. while launcher TextFields are focused.
        if "override fun onKeyDown" in s:
            a,b=method_span(s,"    override fun onKeyDown(")
            s=s[:a]+"""    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean =
        super.onKeyDown(keyCode, event)
"""+s[b:]
        if "override fun onKeyUp" in s:
            a,b=method_span(s,"    override fun onKeyUp(")
            s=s[:a]+"""    override fun onKeyUp(keyCode: Int, event: KeyEvent?): Boolean =
        super.onKeyUp(keyCode, event)
"""+s[b:]
        if "override fun onGenericMotionEvent" in s:
            a,b=method_span(s,"    override fun onGenericMotionEvent(")
            s=s[:a]+"""    override fun onGenericMotionEvent(event: MotionEvent?): Boolean =
        super.onGenericMotionEvent(event)
"""+s[b:]
        return s
    patch(root,rel,f)

def patch_touch_input(root):
    rel="app/src/main/java/com/example/input/TouchInputManager.kt"
    def f(s):
        old='''    fun applySerializedPositions(serialized: String) {
        // legacy
    }'''
        new='''    fun applySerializedPositions(serialized: String) {
        if (serialized.isBlank()) return
        val updated = _legacyButtons.value.toMutableMap()
        serialized.split(";").forEachIndexed { index, token ->
            val parts = token.split(":")
            if (parts.size != 3) {
                LauncherLogger.warn("Ignoring malformed legacy button layout entry $index")
                return@forEachIndexed
            }
            val type = runCatching { VirtualButtonType.valueOf(parts[0]) }.getOrNull()
            val x = parts[1].toFloatOrNull()
            val y = parts[2].toFloatOrNull()
            if (type == null || x == null || y == null) {
                LauncherLogger.warn("Ignoring malformed legacy button layout entry $index")
                return@forEachIndexed
            }
            updated[type] = (updated[type] ?: VirtualButtonState(type)).copy(
                xPercent = x.coerceIn(0.02f, 0.98f),
                yPercent = y.coerceIn(0.02f, 0.98f)
            )
        }
        _legacyButtons.value = updated
    }'''
        if old in s: return s.replace(old,new,1)
        return s
    patch(root,rel,f)

def patch_profiles(root):
    rel="app/src/main/java/com/example/ui/screens/ProfilesScreen.kt"
    def f(s):
        if "val versions by viewModel.versions.collectAsState()" not in s:
            s=s.replace('    val homeState by viewModel.homeUiState.collectAsState()\n',
                        '    val homeState by viewModel.homeUiState.collectAsState()\n    val versions by viewModel.versions.collectAsState()\n',1)
        s=s.replace('var newVersionId by remember { mutableStateOf("1.21.4") }',
                    'var newVersionId by remember(homeState.selectedVersionId) { mutableStateOf(homeState.selectedVersionId) }',1)
        s=s.replace('''                    OutlinedTextField(
                        value = newRamMb,
                        onValueChange = { newRamMb = it },
                        label = { Text("RAM (MB)") },
                        modifier = Modifier.fillMaxWidth()
                    )''',
                    '''                    OutlinedTextField(
                        value = newRamMb,
                        onValueChange = { newRamMb = it.filter(Char::isDigit).take(5) },
                        label = { Text("RAM (MB)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newJvmArgs,
                        onValueChange = { newJvmArgs = it },
                        label = { Text("Custom JVM Arguments") },
                        modifier = Modifier.fillMaxWidth()
                    )''',1)
        s=s.replace('javaVersion = 21,',
                    'javaVersion = viewModel.javaRequirementForVersion(newVersionId),',1)
        return s
    patch(root,rel,f)

def validate(root):
    home=(root/"app/src/main/java/com/example/ui/screens/HomeScreen.kt").read_text(encoding="utf-8")
    if "utilityDialog" in home: raise SystemExit("[second-pass] HomeScreen utilityDialog remains")
    if "ResourcePill(\"●\", \"1,250\"" in home: raise SystemExit("[second-pass] fake resource strip remains")
    touch=(root/"app/src/main/java/com/example/input/TouchInputManager.kt").read_text(encoding="utf-8")
    if "fun applySerializedPositions(serialized: String) {\n        // legacy" in touch: raise SystemExit("[second-pass] legacy no-op remains")
    main=(root/"app/src/main/java/com/example/MainActivity.kt").read_text(encoding="utf-8")
    if "keyboardManager.mapAndroidKeyToMinecraft" in main: raise SystemExit("[second-pass] MainActivity still owns game key routing")
    prof=(root/"app/src/main/java/com/example/ui/screens/ProfilesScreen.kt").read_text(encoding="utf-8")
    if 'mutableStateOf("1.21.4")' in prof or 'javaVersion = 21,' in prof: raise SystemExit("[second-pass] hardcoded profile version/Java remains")

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    patch_home(root)
    patch_main_activity(root)
    patch_touch_input(root)
    patch_profiles(root)
    validate(root)
    print("[second-pass] PASS: Home placeholders, launcher key interception, touch-layout no-op, and profile hardcodes fixed")

if __name__=="__main__":
    main()
