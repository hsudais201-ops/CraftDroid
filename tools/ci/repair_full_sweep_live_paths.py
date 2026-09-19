#!/usr/bin/env python3
"""Live-path fixes found during the full CraftDroid codebase audit."""
from pathlib import Path
import sys

MARKER = "// STEP_FULL_SWEEP_LIVE_FIXES"

def span(src: str, signature: str):
    start = src.find(signature)
    if start < 0:
        raise SystemExit("[live-fixes] missing " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("[live-fixes] missing brace " + signature)
    depth = 0
    state = "code"
    quote = False
    triple = False
    escaped = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
        if state == "line":
            if c == "\n": state = "code"
            i += 1
            continue
        if state == "block":
            if c == "*" and n == "/": state = "code"; i += 2
            else: i += 1
            continue
        if triple:
            if c == '"' and n == '"' and n2 == '"': triple = False; i += 3
            else: i += 1
            continue
        if quote:
            if escaped: escaped = False
            elif c == "\\": escaped = True
            elif c == '"': quote = False
            i += 1
            continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': triple = True; i += 3; continue
        if c == '"': quote = True; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return start, i + 1
        i += 1
    raise SystemExit("[live-fixes] unterminated " + signature)

def replace_method(src: str, signature: str, replacement: str) -> str:
    a, b = span(src, signature)
    return src[:a] + replacement + src[b:]

def patch(root, rel, fn, optional=False):
    p = root / rel
    if not p.is_file():
        if optional:
            return
        raise SystemExit("[live-fixes] missing " + rel)
    p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

def patch_viewmodel(root):
    rel="app/src/main/java/com/example/ui/LauncherViewModel.kt"
    def f(s):
        if MARKER not in s:
            s=s.replace("class LauncherViewModel(", MARKER + "\n\nclass LauncherViewModel(",1)
        install = r'''    fun refreshVersions() {
        viewModelScope.launch {
            _downloadStatusText.value = "Refreshing Minecraft versions…"
            container.versionManager.fetchVersions()
            _downloadStatusText.value = "Minecraft version list refreshed."
        }
    }

    fun javaRequirementForVersion(versionId: String): Int {
        return versions.value.firstOrNull { it.id == versionId }?.javaRequirement ?: when {
            versionId.startsWith("26.") -> 25
            versionId.startsWith("1.20.5") || versionId.startsWith("1.20.6") || versionId.startsWith("1.21") -> 21
            versionId.startsWith("1.17") || versionId.startsWith("1.18") || versionId.startsWith("1.19") || versionId.startsWith("1.20") -> 17
            else -> 8
        }
    }

    fun installSelectedVersion() {
        val current = homeUiState.value
        val versionId = current.selectedVersionId.trim()
        val summary = versions.value.find { it.id == versionId }
        val officialUrl = summary?.url?.takeIf { it.startsWith("https://", true) }
        if (versionId.isBlank() || officialUrl == null) {
            _downloadStatusText.value = "Cannot install " + versionId + ": official version metadata is unavailable."
            LauncherLogger.error("Blocked Minecraft install without official HTTPS metadata URL for version=" + versionId)
            return
        }

        viewModelScope.launch {
            try {
                _downloadStatusText.value = "Installing Minecraft " + versionId + "…"
                val success = container.installer.installVersion(
                    versionId = versionId,
                    versionJsonUrl = officialUrl,
                    onProgress = {},
                    onStatus = { _downloadStatusText.value = it }
                )
                container.versionManager.fetchVersions()
                _downloadStatusText.value = if (success) {
                    "Minecraft " + versionId + " installed successfully."
                } else {
                    "Minecraft " + versionId + " installation failed."
                }
            } catch (e: Exception) {
                LauncherLogger.error("Minecraft installation failed for " + versionId + ": " + e.message)
                _downloadStatusText.value = "Installation failed: " + (e.message ?: "unknown error")
            }
        }
    }'''
        s=replace_method(s,"    fun installSelectedVersion()",install)
        return s
    patch(root,rel,f)

def patch_version_manager(root):
    rel="app/src/main/java/com/example/versions/VersionManager.kt"
    def f(s):
        if MARKER not in s:
            s=s.replace("class VersionManager(", MARKER + "\n\nclass VersionManager(",1)
        s=s.replace(
            '            val response = okHttpClient.newCall(request).execute()\n            val body = response.body?.string() ?: throw IOException("Empty manifest response")',
            '            val response = okHttpClient.newCall(request).execute()\n            if (!response.isSuccessful) throw IOException("Minecraft manifest request failed: HTTP " + response.code)\n            val declaredLength = response.body?.contentLength() ?: -1L\n            if (declaredLength > 8L * 1024L * 1024L) throw IOException("Minecraft manifest is unexpectedly large")\n            val body = response.body?.string() ?: throw IOException("Empty manifest response")',
            1,
        )
        s=s.replace(
            '''                val javaReq = when {
                    id.startsWith("1.21") || id.startsWith("1.20.5") || id.startsWith("1.20.6") -> 21
                    id.startsWith("1.17") || id.startsWith("1.18") || id.startsWith("1.19") || id.startsWith("1.20") -> 17
                    else -> 8
                }''',
            '''                val javaReq = when {
                    id.startsWith("26.") -> 25
                    id.startsWith("1.20.5") || id.startsWith("1.20.6") || id.startsWith("1.21") -> 21
                    id.startsWith("1.17") || id.startsWith("1.18") || id.startsWith("1.19") || id.startsWith("1.20") -> 17
                    else -> 8
                }''',
            1,
        )
        repair = r'''    suspend fun repairVersion(
        versionId: String,
        onProgress: (DownloadProgress) -> Unit,
        onStatus: (String) -> Unit
    ): Boolean = withContext(Dispatchers.IO) {
        val summary = _versionsList.value.find { it.id == versionId }
        val url = summary?.url?.takeIf { it.startsWith("https://", true) }
            ?: throw IOException("Official metadata URL is unavailable for Minecraft version " + versionId)
        LauncherLogger.info("Starting automated repair for " + versionId + "...")
        installer.installVersion(versionId, url, onProgress, onStatus)
    }'''
        if "    suspend fun repairVersion(" in s:
            s=replace_method(s,"    suspend fun repairVersion(",repair)
        return s
    patch(root,rel,f)

def patch_versions_screen(root):
    rel="app/src/main/java/com/example/ui/screens/VersionsScreen.kt"
    def f(s):
        old='''                IconButton(onClick = { viewModel.container.appScope.run { viewModel.container.versionManager.run { viewModel.installSelectedVersion() } } }) {
                    Icon(imageVector = Icons.Default.Refresh, contentDescription = "Refresh Versions")
                }'''
        new='''                IconButton(onClick = { viewModel.refreshVersions() }) {
                    Icon(imageVector = Icons.Default.Refresh, contentDescription = "Refresh Versions")
                }'''
        if old not in s:
            raise SystemExit("[live-fixes] Versions refresh action missing")
        return s.replace(old,new,1)
    patch(root,rel,f)

def patch_game_surface(root):
    rel="app/src/main/java/com/example/game/GameSurfaceView.kt"
    def f(s):
        if "private val keyboardManager = com.example.input.KeyboardManager()" not in s:
            s=s.replace("    private var primaryTouchPointerId: Int? = null\n",
                        "    private var primaryTouchPointerId: Int? = null\n    private val keyboardManager = com.example.input.KeyboardManager()\n",1)
        s=s.replace("    private fun inputKey(keyCode: Int): Int = keyCode",
                    "    private fun inputKey(keyCode: Int): Int = keyboardManager.mapAndroidKeyToMinecraft(keyCode)",1)
        return s
    patch(root,rel,f)

def patch_home(root):
    rel="app/src/main/java/com/example/ui/screens/HomeScreen.kt"
    def f(s):
        s=s.replace('    var utilityDialog by remember { mutableStateOf<String?>(null) }\n','',1)
        old='''            Text("QUICK ACCESS", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black, letterSpacing = 1.5.sp), color = accent)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                QuickAction("Settings", Icons.Default.Settings) { viewModel.navigateTo(LauncherScreen.SETTINGS) }
                QuickAction("Store", Icons.Default.Store) { utilityDialog = "Store" }
                QuickAction("Events", Icons.Default.Event) { utilityDialog = "Events" }
                QuickAction("Ranks", Icons.Default.Leaderboard) { utilityDialog = "Leaderboard" }
                QuickAction("Profile", Icons.Default.Person) { viewModel.navigateTo(LauncherScreen.ACCOUNTS) }
            }'''
        new='''            Text("QUICK ACCESS", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black, letterSpacing = 1.5.sp), color = accent)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                QuickAction("Versions", Icons.AutoMirrored.Filled.List) { viewModel.navigateTo(LauncherScreen.VERSIONS) }
                QuickAction("Profiles", Icons.Default.Build) { viewModel.navigateTo(LauncherScreen.PROFILES) }
                QuickAction("Accounts", Icons.Default.Person) { viewModel.navigateTo(LauncherScreen.ACCOUNTS) }
                QuickAction("Settings", Icons.Default.Settings) { viewModel.navigateTo(LauncherScreen.SETTINGS) }
                QuickAction("Controls", Icons.Default.Gamepad) { viewModel.navigateTo(LauncherScreen.CUSTOMIZE_CONTROLS) }
            }'''
        if old in s:
            s=s.replace(old,new,1)
        old2='''            utilityDialog?.let { name ->
                AlertDialog(
                    onDismissRequest = { utilityDialog = null },
                    title = { Text(name, fontWeight = FontWeight.Black) },
                    text = { Text(if (name == "Notifications") "You have 2 launcher notifications. Store, events and leaderboard services are ready for future online integration." else "$name is part of the premium CraftDroid shell. Online content integration can be connected without changing the launcher navigation.") },
                    confirmButton = { Button(onClick = { utilityDialog = null }) { Text("OK") } }
                )
            }
'''
        s=s.replace(old2,"",1)
        for imp in [
            "import androidx.compose.material.icons.filled.Event\n",
            "import androidx.compose.material.icons.filled.Leaderboard\n",
            "import androidx.compose.material.icons.filled.Store\n",
        ]: s=s.replace(imp,"",1)
        if "import androidx.compose.material.icons.automirrored.filled.List" not in s:
            s=s.replace("import androidx.compose.material.icons.Icons\n","import androidx.compose.material.icons.Icons\nimport androidx.compose.material.icons.automirrored.filled.List\n",1)
        if "import androidx.compose.material.icons.filled.Gamepad" not in s:
            s=s.replace("import androidx.compose.material.icons.filled.Build\n","import androidx.compose.material.icons.filled.Build\nimport androidx.compose.material.icons.filled.Gamepad\n",1)
        return s
    patch(root,rel,f)

def patch_native(root):
    rel="app/src/main/java/com/example/game/NativeGameBridge.kt"
    def f(s):
        s=s.replace("        if (!loaded) return\n        // The order matters:",
                    "        if (!loaded) throw IllegalStateException(\"CraftDroid JNI bridge is unavailable\")\n        // The order matters:",1)
        pairs=[
            ("try { nativeMouse(x, y, dx, dy, button, down) } catch (_: Throwable) { }","try { nativeMouse(x, y, dx, dy, button, down) } catch (t: Throwable) { LauncherLogger.warn(\"JNI mouse input failed: \" + t.message) }"),
            ("try { nativeMouseScroll(horizontal, vertical) } catch (_: Throwable) { }","try { nativeMouseScroll(horizontal, vertical) } catch (t: Throwable) { LauncherLogger.warn(\"JNI mouse-scroll input failed: \" + t.message) }"),
            ("try { nativeKey(key, down, modifiers) } catch (_: Throwable) { }","try { nativeKey(key, down, modifiers) } catch (t: Throwable) { LauncherLogger.warn(\"JNI keyboard input failed: \" + t.message) }"),
            ("try { nativeGamepad(axis, value) } catch (_: Throwable) { }","try { nativeGamepad(axis, value) } catch (t: Throwable) { LauncherLogger.warn(\"JNI gamepad axis failed: \" + t.message) }"),
            ("try { nativeGamepadButton(button, down) } catch (_: Throwable) { }","try { nativeGamepadButton(button, down) } catch (t: Throwable) { LauncherLogger.warn(\"JNI gamepad button failed: \" + t.message) }"),
        ]
        for old,new in pairs: s=s.replace(old,new,1)
        s=s.replace("fun shutdownGlfw() { if (loaded) runCatching { nativeGlfwShutdown() } }",
                    "fun shutdownGlfw() { if (loaded) runCatching { nativeGlfwShutdown() }.onFailure { LauncherLogger.warn(\"GLFW shutdown failed: \" + it.message) } }",1)
        return s
    patch(root,rel,f)

def patch_logger(root):
    patch(root,"app/src/main/java/com/example/logs/LauncherLogger.kt",lambda s:s.replace(
        "        } catch (_: Exception) {}",
        '        } catch (e: Exception) {\n            android.util.Log.w("MCLauncher", "Could not write launcher log file: " + e.message)\n        }',
        1,
    ))


def patch_real_state_defaults(root):
    rel = "app/src/main/java/com/example/auth/AccountProviderType.kt"
    if (root / rel).is_file():
        patch(root, rel, lambda text: text.replace(
            'return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: LOCAL_TEST',
            'return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: MICROSOFT',
            1,
        ))

    rel = "app/src/main/java/com/example/settings/SettingsRepository.kt"
    if (root / rel).is_file():
        def settings(text):
            text = text.replace('val selectedVersionId: String = "1.21.4"', 'val selectedVersionId: String = ""', 1)
            text = text.replace('val enableLocalTestProfiles: Boolean = true', 'val enableLocalTestProfiles: Boolean = false', 1)
            text = text.replace('selectedVersionId = prefs[Keys.SELECTED_VERSION] ?: "1.21.4"', 'selectedVersionId = prefs[Keys.SELECTED_VERSION] ?: ""', 1)
            text = text.replace('enableLocalTestProfiles = prefs[Keys.ENABLE_LOCAL_TEST_PROFILES] ?: true', 'enableLocalTestProfiles = prefs[Keys.ENABLE_LOCAL_TEST_PROFILES] ?: false', 1)
            return text
        patch(root, rel, settings)

    rel = "app/src/main/java/com/example/ui/LauncherViewModel.kt"
    if (root / rel).is_file():
        def vm(text):
            text = text.replace('val selectedVersionId: String = "1.21.4"', 'val selectedVersionId: String = ""', 1)
            anchor = '''            container.versionManager.fetchVersions()
            container.javaManager.refreshRuntimes()'''
            repl = '''            val loadedVersions = container.versionManager.fetchVersions()
            val configuredVersion = container.settingsRepository.settingsFlow.firstOrNull()?.selectedVersionId.orEmpty()
            if (configuredVersion.isBlank() || loadedVersions.none { it.id == configuredVersion }) {
                loadedVersions.firstOrNull()?.id?.let { container.settingsRepository.updateSelectedVersion(it) }
            }
            container.javaManager.refreshRuntimes()'''
            text = text.replace(anchor, repl, 1)
            if "import kotlinx.coroutines.flow.firstOrNull" not in text:
                text = text.replace("import kotlinx.coroutines.flow.combine\n", "import kotlinx.coroutines.flow.combine\nimport kotlinx.coroutines.flow.firstOrNull\n", 1)
            return text
        patch(root, rel, vm)

    rel = "app/src/main/java/com/example/versions/VersionManager.kt"
    if (root / rel).is_file():
        def version_manager(text):
            text = text.replace(
                'val isInstalled = fileSystem.getVersionJarFile(id).exists() && fileSystem.getVersionJsonFile(id).exists()',
                'val isInstalled = isInstalledAndHealthy(id)',
                1,
            )
            text = text.replace(
                '''                        isInstalled = true,
                        javaRequirement = 21
                    )''',
                '''                        isInstalled = isInstalledAndHealthy(id),
                        javaRequirement = runCatching {
                            versionParser.parseVersionDetail(json.readText(Charsets.UTF_8)).javaVersion.majorVersion
                        }.getOrDefault(21)
                    )''',
                1,
            )
            anchor = "    private suspend fun loadLocalVersions(): List<VersionSummary> {"
            helper = '''    private fun isInstalledAndHealthy(versionId: String): Boolean {
        return try {
            val jsonFile = fileSystem.getVersionJsonFile(versionId)
            val jarFile = fileSystem.getVersionJarFile(versionId)
            if (!jsonFile.isFile || !jarFile.isFile) return false
            val detail = versionParser.parseVersionDetail(jsonFile.readText(Charsets.UTF_8))
            if (detail.clientDownload.size > 0L && jarFile.length() != detail.clientDownload.size) return false
            if (detail.clientDownload.sha1.isNotBlank() &&
                !HashVerifier.verifySha1(jarFile, detail.clientDownload.sha1)
            ) return false
            fileSystem.getAssetIndexFile(detail.assetIndex.id).isFile
        } catch (e: Throwable) {
            LauncherLogger.warn("Installed-version integrity check failed for " + versionId + ": " + e.message)
            false
        }
    }

'''
            text = text.replace(anchor, helper + anchor, 1)
            return text
        patch(root, rel, version_manager)


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    patch_real_state_defaults(root)
    patch_viewmodel(root)
    patch_version_manager(root)
    patch_versions_screen(root)
    patch_game_surface(root)
    patch_home(root)
    patch_native(root)
    patch_logger(root)
    print("[live-fixes] PASS: corrected version refresh/install flow, 26.x Java mapping, physical keyboard routing, placeholder UI actions, and JNI error surfacing")

if __name__=="__main__":
    main()
