#!/usr/bin/env python3
"""Step 462: skip touch-card scale animation on low-RAM devices."""
from pathlib import Path
import sys

UI_NAME = "DroidLauncherUiActivity.kt"
MARKER = "// STEP462_LOW_RAM_TOUCH_POLICY"


def find_ui(root: Path) -> Path:
    hits=list((root/"app/src/main/java").rglob(UI_NAME))
    if len(hits)!=1: raise SystemExit(f"[step462] expected one {UI_NAME}, found {len(hits)}")
    return hits[0]


def method_span(s: str, sig: str):
    start=s.find(sig)
    if start<0: raise SystemExit("[step462] missing "+sig)
    brace=s.find("{",start)
    depth=0
    quote=False
    esc=False
    i=brace
    while i<len(s):
        c=s[i]
        if quote:
            if esc: esc=False
            elif c=="\\": esc=True
            elif c=='"': quote=False
            i+=1; continue
        if c=='"': quote=True; i+=1; continue
        if c=="{": depth+=1
        elif c=="}":
            depth-=1
            if depth==0: return start,i+1
        i+=1
    raise SystemExit("[step462] unterminated method "+sig)


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=find_ui(root)
    s=ui.read_text(encoding="utf-8")

    if MARKER in s:
        print("[step462] touch policy already applied")
        return 0

    sig="    private fun step460CategoryCard("
    a,b=method_span(s,sig)
    block=s[a:b]
    old='''            setOnClickListener {
                animate().scaleX(0.97f).scaleY(0.97f).setDuration(55).withEndAction {
                    scaleX = 1f
                    scaleY = 1f
                    action()
                }.start()
            }'''
    new='''            setOnClickListener {
                if (step376LowRam) {
                    action()
                } else {
                    animate().scaleX(0.97f).scaleY(0.97f).setDuration(55).withEndAction {
                        scaleX = 1f
                        scaleY = 1f
                        action()
                    }.start()
                }
            }'''
    if old not in block: raise SystemExit("[step462] category touch animation block not found")
    block=block.replace(old,new,1)
    s=s[:a]+block+s[b:]
    s=s[:a]+s[a:b].replace("    private fun step460CategoryCard(", "    // STEP462_LOW_RAM_TOUCH_POLICY\n    private fun step460CategoryCard(",1)+s[b:]
    ui.write_text(s,encoding="utf-8")
    print("[step462] low-RAM category-card touch animation disabled; normal devices retain feedback")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
