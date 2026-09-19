#!/usr/bin/env python3
"""Step 479: final premium UI repair."""
from pathlib import Path
import sys

MARKER = "// STEP479_PREMIUM_UI"

def span(s, sig):
    a=s.find(sig)
    if a<0: raise SystemExit("[step479] missing "+sig)
    b0=s.find("{",a)
    if b0<0: raise SystemExit("[step479] no brace "+sig)
    d=0; state="code"; esc=False; i=b0
    while i<len(s):
        c=s[i]; n=s[i+1] if i+1<len(s) else ""; n2=s[i+2] if i+2<len(s) else ""
        if state=="line":
            if c=="\n": state="code"
            i+=1; continue
        if state=="block":
            if c=="*" and n=="/": state="code"; i+=2
            else: i+=1
            continue
        if state=="triple":
            if c=='"' and n=='"' and n2=='"': state="code"; i+=3
            else: i+=1
            continue
        if state=="string":
            if esc: esc=False
            elif c=="\\": esc=True
            elif c=='"': state="code"
            i+=1; continue
        if c=="/" and n=="/": state="line"; i+=2; continue
        if c=="/" and n=="*": state="block"; i+=2; continue
        if c=='"' and n=='"' and n2=='"': state="triple"; i+=3; continue
        if c=='"': state="string"; i+=1; continue
        if c=="{": d+=1
        elif c=="}":
            d-=1
            if d==0: return a,i+1
        i+=1
    raise SystemExit("[step479] unterminated "+sig)

def replace(s,sig,new):
    a,b=span(s,sig); return s[:a]+new+s[b:]

HELPERS=r'''
    // STEP479_PREMIUM_UI
    private fun step479Card(titleText:String, detail:String, badge:String, action:()->Unit)=LinearLayout(this).apply{
        orientation=LinearLayout.VERTICAL; setPadding(dp(13),dp(11),dp(13),dp(11))
        background=android.graphics.drawable.GradientDrawable().apply{
            cornerRadius=dp(18).toFloat()
            setColor(android.graphics.Color.argb(235,12,19,30))
            setStroke(dp(1),android.graphics.Color.argb(120,65,235,170))
        }
        elevation=if(step376LowRam) dp(1).toFloat() else dp(4).toFloat()
        addView(step460MiniBadge(badge),LinearLayout.LayoutParams(dp(52),dp(38)))
        addView(step375Text(titleText,16f,true).apply{setPadding(0,dp(7),0,dp(1))})
        addView(step375Text(detail,10.5f).apply{setTextColor(android.graphics.Color.argb(185,210,228,238))})
        isClickable=true; isFocusable=true; setOnClickListener{action()}
    }

    private fun step479Row(titleText:String,detail:String,buttonText:String,fill:Boolean=true,action:()->Unit)=LinearLayout(this).apply{
        orientation=LinearLayout.HORIZONTAL; gravity=Gravity.CENTER_VERTICAL
        setPadding(dp(12),dp(8),dp(10),dp(8))
        background=android.graphics.drawable.GradientDrawable().apply{
            cornerRadius=dp(16).toFloat()
            setColor(android.graphics.Color.argb(225,13,21,32))
            setStroke(dp(1),android.graphics.Color.argb(75,90,220,180))
        }
        val c=LinearLayout(this@DroidLauncherUiActivity).apply{orientation=LinearLayout.VERTICAL
            addView(step375Text(titleText,14f,true))
            addView(step375Text(detail,10.5f).apply{setTextColor(android.graphics.Color.argb(175,205,225,235))})
        }
        addView(c,LinearLayout.LayoutParams(0,dp(58),1f))
        addView(step375Button(buttonText,fill,action),LinearLayout.LayoutParams(dp(118),dp(44)))
    }

    private fun step479FirstRun(){
        pageArea.addView(step375Title("Welcome to CraftDroid","Install the launcher workspace once, then use the premium dashboard."))
        val row=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        val left=step375Panel(18)
        left.addView(step460LogoBadge("CD",62),LinearLayout.LayoutParams(dp(62),dp(62)))
        left.addView(step375Text("Minecraft Java Launcher",24f,true).apply{setPadding(0,dp(12),0,dp(4))})
        left.addView(step375Text("Create writable launcher folders and prepare download paths. Minecraft versions and Java runtimes are installed on demand.",12f).apply{setTextColor(android.graphics.Color.argb(190,215,232,240))})
        left.addView(step375Button("INSTALL & CONTINUE",true){
            android.app.AlertDialog.Builder(this).setTitle("Preparing CraftDroid").setMessage("Checking launcher storage and download paths…").setCancelable(false).create().also{d->
                d.show()
                step376PrepareFirstRun{ok,msg->
                    d.dismiss()
                    if(ok){step375Prefs().edit().putBoolean("installed",true).apply();showPage("Home")}
                    else android.widget.Toast.makeText(this@DroidLauncherUiActivity,"Setup failed: "+msg,android.widget.Toast.LENGTH_LONG).show()
                }
            }
        },LinearLayout.LayoutParams(-1,dp(56)).apply{topMargin=dp(14)})
        row.addView(left,LinearLayout.LayoutParams(0,dp(360),.58f))
        val right=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        right.addView(step479Card("Minecraft Versions","Install 26.3, 26.2, 26.1.2, 26.1.1 or latest.","MC"){showPage("Versions")},LinearLayout.LayoutParams(-1,0,1f))
        right.addView(step479Card("Content Library","Mods, modpacks, shaders, resource packs and worlds.","LIB"){showPage("Content")},LinearLayout.LayoutParams(-1,0,1f).apply{topMargin=dp(8)})
        right.addView(step479Card("Java Runtime","Automatic Java 8 / 17 / 21 / 25 selection.","JAVA"){showPage("Java")},LinearLayout.LayoutParams(-1,0,1f).apply{topMargin=dp(8)})
        row.addView(right,LinearLayout.LayoutParams(0,dp(360),.42f).apply{marginStart=dp(10)})
        pageArea.addView(row)
    }

    private fun step479Home(){
        pageArea.addView(step375Title("Minecraft Dashboard",if(step375HasInstance()) "\${step375SelectedInstance()} · \${selectedMinecraftVersion()}" else "Select an instance and install a Minecraft version."))
        val hero=step375Panel(16)
        hero.addView(step375Text("CRAFTDROID · MINECRAFT JAVA",11f,true).apply{setTextColor(android.graphics.Color.rgb(70,235,165))})
        hero.addView(step375Text(if(step375HasInstance()) "Ready to play" else "Your launcher is ready",25f,true))
        hero.addView(step375Text(if(step375HasInstance()) "Version \${selectedMinecraftVersion()} · manage content or launch." else "Start by selecting an instance.",12f).apply{setTextColor(android.graphics.Color.argb(185,210,228,238))})
        val actions=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        actions.addView(step375Button("▶ PLAY",true){if(!step375HasInstance())showPage("Instances") else if(selectedAccountIndex()<0)showPage("Accounts") else launchSelectedMinecraft()},LinearLayout.LayoutParams(0,dp(52),1f))
        actions.addView(step375Button("INSTALL VERSION"){showPage("Versions")},LinearLayout.LayoutParams(0,dp(52),1f).apply{marginStart=dp(8)})
        actions.addView(step375Button("SERVERS"){showPage("Servers")},LinearLayout.LayoutParams(0,dp(52),1f).apply{marginStart=dp(8)})
        hero.addView(actions,LinearLayout.LayoutParams(-1,dp(52)).apply{topMargin=dp(12)})
        pageArea.addView(hero)
        pageArea.addView(step375Title("Library","All content is stored per selected instance."))
        val defs=listOf(
            arrayOf("Mods","MOD","JAR mods") to "Mod",
            arrayOf("Modpacks","PACK","MRPACK / ZIP") to "Modpack",
            arrayOf("Shaders","FX","Shader packs") to "Shader Pack",
            arrayOf("Resource Packs","RES","Textures & UI") to "Resource Pack",
            arrayOf("Worlds","WRLD","Saved worlds") to "World",
            arrayOf("Versions","MC","Minecraft installs") to "Versions"
        )
        val grid=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        for(r in 0..1){
            val line=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
            for(c in 0..2){
                val d=defs[r*3+c].first; val target=defs[r*3+c].second
                line.addView(step479Card(d[0],d[2],d[1]){if(target=="Versions")showPage("Versions")else showPage(target)},LinearLayout.LayoutParams(0,dp(132),1f).apply{if(c>0)marginStart=dp(8)})
            }
            grid.addView(line,LinearLayout.LayoutParams(-1,dp(132)).apply{if(r>0)topMargin=dp(8)})
        }
        pageArea.addView(grid)
    }

    private fun step479Content(){
        pageArea.addView(step375Title("Content Library","Choose a manager. Each manager has a real Android import action."))
        val defs=listOf(
            arrayOf("Mods","MOD","Import .jar") to "Mod",
            arrayOf("Modpacks","PACK","Import .mrpack") to "Modpack",
            arrayOf("Shaders","FX","Import shader pack") to "Shader Pack",
            arrayOf("Resource Packs","RES","Import textures") to "Resource Pack",
            arrayOf("Worlds","WRLD","Import world") to "World",
            arrayOf("Versions","MC","Install Minecraft") to "Versions"
        )
        val grid=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        for(r in 0..1){
            val line=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
            for(c in 0..2){
                val d=defs[r*3+c].first; val target=defs[r*3+c].second
                line.addView(step479Card(d[0],d[2],d[1]){if(target=="Versions")showPage("Versions")else showPage(target)},LinearLayout.LayoutParams(0,dp(132),1f).apply{if(c>0)marginStart=dp(8)})
            }
            grid.addView(line,LinearLayout.LayoutParams(-1,dp(132)).apply{if(r>0)topMargin=dp(8)})
        }
        pageArea.addView(grid)
    }

    private fun step479Manager(type:String){
        val title=when(type){"Mod"->"Mods";"Modpack"->"Modpacks";"Shader Pack"->"Shaders";"Resource Pack"->"Resource Packs";"World"->"Worlds";else->type}
        val desc=when(type){"Mod"->"Import JAR mods into the selected instance.";"Modpack"->"Import MRPACK or supported archives.";"Shader Pack"->"Import shader packs for the active renderer.";"Resource Pack"->"Import texture and UI packs.";"World"->"Import Minecraft world archives.";else->"Manage content."}
        pageArea.addView(step375Title(title,desc))
        val p=step375Panel(18)
        p.addView(step460MiniBadge(step460Glyph(type)),LinearLayout.LayoutParams(dp(60),dp(44)))
        p.addView(step375Text("Import \${title}",21f,true).apply{setPadding(0,dp(12),0,dp(4))})
        p.addView(step375Text("The Android document picker opens only when you press Import. Processing happens off the UI thread.",11f).apply{setTextColor(android.graphics.Color.argb(180,205,225,235))})
        p.addView(step375Button("IMPORT \${title.uppercase()}",true){if(!step375HasInstance())showPage("Instances")else step391StartContentImport(type)},LinearLayout.LayoutParams(-1,dp(52)).apply{topMargin=dp(14)})
        pageArea.addView(p)
    }

    private fun step479Versions(){
        pageArea.addView(step375Title("Minecraft Versions","Install releases into the selected instance. Latest is refreshed from Mojang metadata."))
        val actions=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        actions.addView(step375Button("REFRESH LATEST"){refreshLatestMinecraftVersion();showPage("Versions")},LinearLayout.LayoutParams(0,dp(46),1f))
        actions.addView(step375Button("JAVA RUNTIME"){showPage("Java")},LinearLayout.LayoutParams(0,dp(46),1f).apply{marginStart=dp(8)})
        pageArea.addView(actions)
        if(!step375HasInstance()){
            val p=step375Panel(18);p.addView(step375Text("SELECT AN INSTANCE FIRST",20f,true));p.addView(step375Text("Minecraft files are isolated per instance."));p.addView(step375Button("SELECT INSTANCE",true){showPage("Instances")},LinearLayout.LayoutParams(-1,dp(50)).apply{topMargin=dp(10)});pageArea.addView(p,LinearLayout.LayoutParams(-1,dp(190)).apply{topMargin=dp(8)});return
        }
        minecraftVersionChoices().forEach{version->
            val installed=MinecraftVersionInstallManager.isInstalled(this,version)
            pageArea.addView(step479Row(version,if(version==MinecraftLatestVersionManager.getCached(this))"Latest detected by Mojang" else "Minecraft Java Edition",if(installed)"SELECT" else "INSTALL",installed){
                if(installed){saveMinecraftVersion(version);showPage("Home")}else installMinecraftVersion(version)
            },LinearLayout.LayoutParams(-1,dp(76)).apply{topMargin=dp(7)})
        }
    }

    private fun step479Servers(){
        pageArea.addView(step375Title("Servers","Clean server cards with Add, Select, Edit, Delete and background reachability checks."))
        val top=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        top.addView(step375Button("+ ADD SERVER",true){showServerDialog(-1)},LinearLayout.LayoutParams(0,dp(48),1f))
        top.addView(step375Button("REFRESH ALL"){getSavedServers().forEach{refreshServerStatus(it.first,it.second)};showPage("Servers")},LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(8)})
        pageArea.addView(top)
        val selected=getSharedPreferences("droid_launcher",MODE_PRIVATE).getString("selected_server","") ?: ""
        val list=getSavedServers()
        if(list.isEmpty()){
            val p=step375Panel(20);p.gravity=Gravity.CENTER;p.addView(step460MiniBadge("SRV"));p.addView(step375Text("No servers saved",20f,true));p.addView(step375Text("Add a server such as play.example.com:25565."));pageArea.addView(p,LinearLayout.LayoutParams(-1,dp(200)).apply{topMargin=dp(8)});return
        }
        list.forEachIndexed{index,s->
            val host=s.first;val port=s.second;val chosen="$host:$port"==selected
            val row=step479Row(getServerName(index).ifBlank{host},"$host:$port  ·  "+getServerStatus(host,port)+(if(chosen)"  · SELECTED" else ""),"SELECT",chosen){selectServer(host,port);showPage("Servers")}
            row.addView(step375Button("EDIT"){showServerDialog(index)},LinearLayout.LayoutParams(dp(78),dp(42)).apply{marginStart=dp(5)})
            row.addView(step375Button("DELETE"){deleteServer(index);showPage("Servers")},LinearLayout.LayoutParams(dp(82),dp(42)).apply{marginStart=dp(5)})
            pageArea.addView(row,LinearLayout.LayoutParams(-1,dp(76)).apply{topMargin=dp(7)})
        }
    }
'''

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=root/"app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step479] UI missing")
    s=ui.read_text(encoding="utf-8")
    if MARKER not in s:
        s=s[:s.find("    override fun onCreate(")]+HELPERS+"\n"+s[s.find("    override fun onCreate("):]
    s=replace(s,"    override fun onCreate(",'''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation=android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        window.setFlags(android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN,android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN)
        buildUi()
        if(step375Prefs().getBoolean("installed",false)) showPage("Home") else showPage("FirstRun")
    }''')
    s=replace(s,"    private fun showPage(page: String)",'''    private fun showPage(page: String) {
        if(page!="FirstRun" && !step375Prefs().getBoolean("installed",false)){showPage("FirstRun");return}
        currentPage=page;pageArea.removeAllViews()
        when(page){
            "FirstRun"->step479FirstRun()
            "Home","Game"->step479Home()
            "Content","Downloads"->step479Content()
            "Mod"->step479Manager("Mod")
            "Modpack"->step479Manager("Modpack")
            "Shader Pack","Shaders"->step479Manager("Shader Pack")
            "Resource Pack","Resource Packs"->step479Manager("Resource Pack")
            "World","Worlds"->step479Manager("World")
            "Versions"->step479Versions()
            "Servers"->step479Servers()
            "Instances"->step375Instances()
            "Accounts"->step375Accounts()
            "Microsoft"->step375AccountDetail(true)
            "Offline"->step375AccountDetail(false)
            "Settings","Renderer"->step375Settings()
            "Features"->aboutPage()
            "Controls"->controlsPage()
            "Java"->javaPage()
            else->step479Content()
        }
        pageArea.alpha=1f;pageArea.translationY=0f
    }''')
    required=("INSTALL & CONTINUE","step479Home()","step479Content()","step479Manager(type:String)","step479Versions()","step479Servers()","installMinecraftVersion(version)","MinecraftVersionInstallManager.isInstalled","showServerDialog(-1)","step391StartContentImport(type)")
    for x in required:
        if x not in s: raise SystemExit("[step479] missing "+x)
    ui.write_text(s,encoding="utf-8")
    print("[step479] premium UI + first-run install + content managers + version install + server manager installed")

if __name__=="__main__": main()
