#!/usr/bin/env python3
"""Step 286: replace the launcher shell with the supplied Home + Account GUI.

This runs after the existing server/launch/feature generators, so it changes only
presentation/navigation and keeps the generated launch/server methods intact.
"""
from pathlib import Path
import re
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step286] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step286] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step286] method opening brace not found: {signature}")
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit(f"[step286] unterminated method: {signature}")


def replace_method(source: str, signature: str, replacement: str) -> str:
    start, end = method_block(source, signature)
    return source[:start] + replacement + source[end:]


BUILD_UI = r'''    private fun buildUi() {
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }

        val top = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(4), dp(10), dp(4))
        }
        title.text = "Droid Launcher"
        title.textSize = 20f
        title.setTextColor(text)
        title.typeface = Typeface.DEFAULT_BOLD
        top.addView(title, LinearLayout.LayoutParams(0, dp(52), 1f))

        val home = button("⌂")
        home.setOnClickListener { showPage("Game") }
        val accounts = button("♟")
        accounts.setOnClickListener { showPage("Accounts") }
        val downloads = button("⇩")
        downloads.setOnClickListener { showPage("Search by ID") }
        val settings = button("⚙")
        settings.setOnClickListener { showPage("Renderer") }
        listOf(home, accounts, downloads, settings).forEach {
            top.addView(it, LinearLayout.LayoutParams(dp(52), dp(52)))
        }
        root.addView(top, LinearLayout.LayoutParams(-1, dp(60)))

        val body = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(12), dp(6), dp(12), dp(12))
        }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        scroll.addView(pageArea)
        pageArea.orientation = LinearLayout.VERTICAL
        pageArea.setPadding(dp(2), dp(2), dp(2), dp(10))
        body.addView(scroll, LinearLayout.LayoutParams(0, -1, 1f))
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }'''

SHOW_PAGE = r'''    private fun showPage(page: String) {
        currentPage = page
        title.text = when (page) {
            "Game" -> "Droid Launcher"
            "Accounts" -> "Accounts / Profiles"
            else -> "Droid Launcher  ·  $page"
        }
        pageArea.removeAllViews()
        when (page) {
            "Game" -> homePage()
            "Accounts" -> accountPage()
            "Renderer" -> rendererPage()
            "Java" -> javaPage()
            "Controls" -> controlsPage()
            "Modpack", "Mod", "Resource Pack", "Saves", "Shader Pack", "Search by ID" -> libraryPage(page)
            else -> aboutPage()
        }
    }'''

HOME_PAGE = r'''    private fun homePage() {
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.TOP
        }

        val left = cardView(12).apply { setPadding(dp(12), dp(10), dp(12), dp(10)) }
        val toolbar = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        toolbar.addView(label("Servers", 18f, true), LinearLayout.LayoutParams(0, dp(44), 1f))

        val add = button("Add Server", true)
        add.setOnClickListener { showServerDialog(-1) }
        val edit = button("Edit")
        edit.setOnClickListener {
            val selected = getSelectedServerIndex()
            if (selected >= 0) showServerDialog(selected) else showServerDialog(-1)
        }
        val refresh = button("refresh")
        refresh.setOnClickListener { refreshAllServers() }
        toolbar.addView(add, LinearLayout.LayoutParams(dp(118), dp(44)))
        toolbar.addView(edit, LinearLayout.LayoutParams(dp(82), dp(44)))
        toolbar.addView(refresh, LinearLayout.LayoutParams(dp(100), dp(44)))
        left.addView(toolbar)
        left.addView(label("Saved servers · status updates are live when checked", 12f, false))

        val servers = getSavedServers()
        if (servers.isEmpty()) {
            val empty = label("No servers yet\nTap Add Server to create your first server.", 15f, true)
            empty.gravity = Gravity.CENTER
            left.addView(empty, LinearLayout.LayoutParams(-1, dp(150)))
        } else {
            servers.forEachIndexed { index, server ->
                val row = LinearLayout(this).apply {
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(dp(6), dp(4), dp(4), dp(4))
                }
                val avatar = TextView(this).apply {
                    text = "▣"
                    textSize = 22f
                    gravity = Gravity.CENTER
                    setTextColor(text)
                    background = android.graphics.drawable.GradientDrawable().apply {
                        shape = android.graphics.drawable.GradientDrawable.RECTANGLE
                        cornerRadius = dp(12).toFloat()
                        setColor(Color.WHITE)
                    }
                }
                row.addView(avatar, LinearLayout.LayoutParams(dp(54), dp(54)))
                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val name = getServerName(index).ifBlank { server.first }
                info.addView(label(name, 15f, true))
                info.addView(label(server.first + ":" + server.second, 11f, false))
                val status = getServerStatus(server.first, server.second)
                info.addView(label(status, 12f, true))
                row.addView(info, LinearLayout.LayoutParams(0, dp(68), 1f))

                val check = button("Check", true)
                check.setOnClickListener { refreshServerStatus(server.first, server.second) }
                row.addView(check, LinearLayout.LayoutParams(dp(74), dp(46)))
                val del = button("Delete")
                del.setOnClickListener { deleteServer(index); showPage("Game") }
                row.addView(del, LinearLayout.LayoutParams(dp(78), dp(46)))
                row.setOnClickListener { selectServer(server.first, server.second); showPage("Game") }
                left.addView(row, LinearLayout.LayoutParams(-1, dp(72)))
            }
        }
        body.addView(left, LinearLayout.LayoutParams(0, -1, 0.70f))

        val right = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), 0, 0, 0)
        }
        val accountCard = cardView(16).apply { gravity = Gravity.CENTER_HORIZONTAL }
        accountCard.addView(label("Account", 17f, true))
        val selected = selectedAccountIndex()
        if (selected >= 0) {
            val name = accountName(selected)
            accountAvatar(accountCard, name)
            accountCard.addView(label(name, 18f, true))
            accountCard.addView(label(accountType(selected), 12f, false))
        } else {
            accountAvatar(accountCard, "+")
            accountCard.addView(label("Add Account", 16f, true))
            accountCard.addView(label("Choose a profile before launching", 12f, false))
        }
        val manage = button("Manage Accounts")
        manage.setOnClickListener { showPage("Accounts") }
        accountCard.addView(manage, LinearLayout.LayoutParams(-1, dp(46)))
        right.addView(accountCard, LinearLayout.LayoutParams(-1, 0, 1f))

        val launch = button("Launch", true)
        launch.textSize = 18f
        launch.setOnClickListener {
            if (selectedAccountIndex() < 0) showPage("Accounts") else launchSelectedMinecraft()
        }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(68)).apply { topMargin = dp(10) })
        body.addView(right, LinearLayout.LayoutParams(0, -1, 0.30f))
        pageArea.addView(body, LinearLayout.LayoutParams(-1, -1))
    }

    private fun accountAvatar(parent: LinearLayout, value: String) {
        val avatar = TextView(this).apply {
            text = if (value.length <= 2) value else value.take(2).uppercase()
            textSize = 24f
            gravity = Gravity.CENTER
            setTextColor(text)
            background = android.graphics.drawable.GradientDrawable().apply {
                shape = android.graphics.drawable.GradientDrawable.OVAL
                setColor(Color.WHITE)
                setStroke(dp(2), accent)
            }
        }
        parent.addView(avatar, LinearLayout.LayoutParams(dp(76), dp(76)).apply { bottomMargin = dp(8) })
    }

    private fun accountPrefs(): android.content.SharedPreferences =
        getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)

    private fun accountCount(): Int = accountPrefs().getInt("count", 0).coerceAtLeast(0)

    private fun accountName(index: Int): String =
        accountPrefs().getString("name_$index", "Profile ${index + 1}") ?: "Profile ${index + 1}"

    private fun accountType(index: Int): String =
        accountPrefs().getString("type_$index", "Offline") ?: "Offline"

    private fun selectedAccountIndex(): Int = accountPrefs().getInt("selected", -1).takeIf { it in 0 until accountCount() } ?: -1

    private fun addAccount(type: String, name: String) {
        val clean = name.trim().ifBlank { "Player" }
        val count = accountCount()
        accountPrefs().edit()
            .putInt("count", count + 1)
            .putString("name_$count", clean)
            .putString("type_$count", type)
            .putInt("selected", count)
            .apply()
        showPage("Accounts")
    }

    private fun editAccount(index: Int) {
        if (index !in 0 until accountCount()) return
        val input = android.widget.EditText(this).apply { setText(accountName(index)); singleLine = true; hint = "Profile name" }
        android.app.AlertDialog.Builder(this).setTitle("Edit Profile").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                accountPrefs().edit().putString("name_$index", input.text.toString().trim().ifBlank { accountName(index) }).apply()
                showPage("Accounts")
            }.show()
    }

    private fun deleteAccount(index: Int) {
        if (index !in 0 until accountCount()) return
        val count = accountCount()
        val e = accountPrefs().edit()
        for (i in index until count - 1) {
            e.putString("name_$i", accountName(i + 1))
                .putString("type_$i", accountType(i + 1))
        }
        e.remove("name_${count - 1}").remove("type_${count - 1}").putInt("count", count - 1)
        val next = if (count - 1 <= 0) -1 else minOf(index, count - 2)
        e.putInt("selected", next).apply()
    }

    private fun showMicrosoftAccountInfo() {
        android.app.AlertDialog.Builder(this)
            .setTitle("Microsoft account")
            .setMessage("Microsoft sign-in is kept separate from local profiles. Connect the launcher OAuth client here when its client configuration is available; this button does not fake a successful login.")
            .setNegativeButton("Close", null)
            .setPositiveButton("Continue") { _, _ ->
                android.widget.Toast.makeText(this, "Microsoft authentication configuration is required.", android.widget.Toast.LENGTH_LONG).show()
            }.show()
    }

    private fun showOfflineAccountDialog() {
        val input = android.widget.EditText(this).apply { hint = "Minecraft username"; singleLine = true }
        android.app.AlertDialog.Builder(this).setTitle("Add Offline Account").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ -> addAccount("Offline", input.text.toString()) }.show()
    }

    private fun showCustomAccountDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(24), 0, dp(24), 0) }
        val provider = android.widget.EditText(this).apply { hint = "Provider / method"; singleLine = true }
        val name = android.widget.EditText(this).apply { hint = "Username"; singleLine = true }
        box.addView(provider, LinearLayout.LayoutParams(-1, dp(54)))
        box.addView(name, LinearLayout.LayoutParams(-1, dp(54)))
        android.app.AlertDialog.Builder(this).setTitle("Add Another Account Method").setView(box)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ -> addAccount(provider.text.toString().trim().ifBlank { "Custom" }, name.text.toString()) }.show()
    }

    private fun accountPage() {
        val chooser = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val ms = button("add Microsoft\naccount")
        ms.setOnClickListener { showMicrosoftAccountInfo() }
        val offline = button("add Offline\naccount")
        offline.setOnClickListener { showOfflineAccountDialog() }
        val other = button("add another\nway to add\naccount")
        other.setOnClickListener { showCustomAccountDialog() }
        chooser.addView(ms, LinearLayout.LayoutParams(0, dp(76), 1f))
        chooser.addView(offline, LinearLayout.LayoutParams(0, dp(76), 1f))
        chooser.addView(other, LinearLayout.LayoutParams(0, dp(76), 1f))
        pageArea.addView(chooser)

        val list = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.TOP }
        val count = accountCount()
        if (count == 0) {
            val empty = cardView(18).apply { gravity = Gravity.CENTER }
            accountAvatar(empty, "+")
            empty.addView(label("No profiles yet", 18f, true))
            empty.addView(label("Add Microsoft, Offline, or another supported method above.", 12f, false))
            list.addView(empty, LinearLayout.LayoutParams(-1, dp(240)))
        } else {
            for (i in 0 until count) {
                val card = cardView(14).apply { gravity = Gravity.CENTER_HORIZONTAL }
                accountAvatar(card, accountName(i))
                card.addView(label(accountName(i), 16f, true))
                card.addView(label(accountType(i), 12f, false))
                val selected = i == selectedAccountIndex()
                val select = button(if (selected) "Selected" else "▶")
                select.setOnClickListener { accountPrefs().edit().putInt("selected", i).apply(); showPage("Accounts") }
                val actions = LinearLayout(this).apply { gravity = Gravity.CENTER }
                val del = button("⌫")
                del.setOnClickListener { deleteAccount(i); showPage("Accounts") }
                val edit = button("✎")
                edit.setOnClickListener { editAccount(i) }
                actions.addView(del, LinearLayout.LayoutParams(dp(54), dp(46)))
                actions.addView(edit, LinearLayout.LayoutParams(dp(54), dp(46)))
                actions.addView(select, LinearLayout.LayoutParams(dp(70), dp(46)))
                card.addView(actions)
                list.addView(card, LinearLayout.LayoutParams(dp(220), dp(250)).apply { marginEnd = dp(12) })
            }
        }
        val cards = ScrollView(this).apply { isHorizontalScrollBarEnabled = true }
        cards.addView(list)
        pageArea.addView(cards, LinearLayout.LayoutParams(-1, dp(280)))

        val home = button("⌂  Home")
        home.setOnClickListener { showPage("Game") }
        pageArea.addView(home, LinearLayout.LayoutParams(dp(150), dp(52)))
    }

    private fun getSelectedServerIndex(): Int {
        val selected = getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("selected_server", "") ?: ""
        return getSavedServers().indexOfFirst { it.first + ":" + it.second == selected }
    }

    private fun refreshAllServers() {
        getSavedServers().forEach { refreshServerStatus(it.first, it.second) }
        showPage("Game")
    }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    s = ui.read_text(encoding="utf-8")

    s = replace_method(s, "    private fun buildUi()", BUILD_UI)
    s = replace_method(s, "    private fun showPage(page: String)", SHOW_PAGE)

    if "    private fun homePage()" not in s:
        anchor = "    private fun rendererPage() {"
        if anchor not in s:
            raise SystemExit("[step286] rendererPage anchor missing")
        s = s.replace(anchor, HOME_PAGE + "\n\n" + anchor, 1)

    # The old Game page remains available as dead code only if another generator
    # references it. Navigation now consistently enters homePage().
    ui.write_text(s, encoding="utf-8")
    print("[step286] Home GUI applied from first supplied mockup")
    print("[step286] Account/Profile GUI applied from second supplied mockup")
    print("[step286] Server add/edit/refresh/status and launch wiring preserved")
    print("[step286] Offline/custom profiles persist locally; Microsoft button does not fake authentication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
