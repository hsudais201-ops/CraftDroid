package com.example

import android.os.Bundle
import android.view.KeyEvent
import android.view.MotionEvent
import android.content.pm.ActivityInfo
import android.content.Intent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import com.example.ui.screens.ServerBrowserScreen
import com.example.ui.screens.OnboardingScreen
import com.example.ui.screens.ContentBrowserScreen
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.testTag
import com.example.core.LauncherContainer
import com.example.launcher.LaunchState
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import com.example.ui.components.RepairDialog
import com.example.ui.screens.AccountsScreen
import com.example.ui.screens.CustomizeControlsScreen
import com.example.ui.screens.GameLaunchOverlay
import com.example.ui.screens.HomeScreen
import com.example.ui.screens.LogsScreen
import com.example.ui.screens.ProfilesScreen
import com.example.ui.screens.SettingsScreen
import com.example.ui.screens.VersionsScreen
import com.example.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {

    private val container by lazy { LauncherContainer.get(applicationContext) }
    private val viewModel: LauncherViewModel by viewModels { LauncherViewModel.Factory(container) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        enableEdgeToEdge()

        setContent {
            MyApplicationTheme {
                MainAppContent(viewModel = viewModel)
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (event != null) {
            val mcKey = container.keyboardManager.mapAndroidKeyToMinecraft(keyCode)
            if (mcKey != -1) {
                return true
            }
            val controllerKey = container.controllerManager.handleKeyEvent(event)
            if (controllerKey != null) {
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent?): Boolean {
        if (event != null) {
            val mcKey = container.keyboardManager.mapAndroidKeyToMinecraft(keyCode)
            if (mcKey != -1) {
                return true
            }
        }
        return super.onKeyUp(keyCode, event)
    }

    override fun onGenericMotionEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            container.controllerManager.handleGenericMotionEvent(event)
            return true
        }
        return super.onGenericMotionEvent(event)
    }
}

@Composable
fun MainAppContent(viewModel: LauncherViewModel) {
    val currentScreen by viewModel.currentScreen.collectAsState()
    val launchState by viewModel.launchState.collectAsState()
    val homeUiState by viewModel.homeUiState.collectAsState()
    val settings by viewModel.settings.collectAsState()
    val versions by viewModel.versions.collectAsState()
    val welcomeDismissedState = androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    val welcomeDismissed = welcomeDismissedState.value

    val context = androidx.compose.ui.platform.LocalContext.current
    val hasInstalledVersion = versions.any { it.isInstalled }
    val onboardingRequired = !settings.onboardingComplete && !hasInstalledVersion

    LaunchedEffect(onboardingRequired) {
        if (!onboardingRequired) welcomeDismissedState.value = true
    }

    LaunchedEffect(launchState) {
        if (launchState is LaunchState.Running) {
            context.startActivity(Intent(context, com.example.game.GameActivity::class.java))
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = Color.Transparent,
        bottomBar = {
            if (launchState is LaunchState.Idle && currentScreen != LauncherScreen.CUSTOMIZE_CONTROLS && !(onboardingRequired && !welcomeDismissed)) {
                androidx.compose.material3.Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 10.dp)
                        .clip(RoundedCornerShape(24.dp)),
                    color = androidx.compose.material3.MaterialTheme.colorScheme.surface.copy(alpha = 0.96f),
                    tonalElevation = 10.dp,
                    shadowElevation = 10.dp
                ) {
                    NavigationBar(
                        modifier = Modifier.testTag("launcher_bottom_bar"),
                        containerColor = Color.Transparent,
                        tonalElevation = 0.dp
                    ) {
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.HOME,
                            onClick = { viewModel.navigateTo(LauncherScreen.HOME) },
                            icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                            label = { Text("Home") },
                            modifier = Modifier.testTag("nav_home")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.CONTENT,
                            onClick = { viewModel.navigateTo(LauncherScreen.CONTENT) },
                            icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Browse") },
                            label = { Text("Browse") },
                            modifier = Modifier.testTag("nav_browse")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.SERVERS,
                            onClick = { viewModel.navigateTo(LauncherScreen.SERVERS) },
                            icon = { Icon(Icons.Default.Info, contentDescription = "Servers") },
                            label = { Text("Servers") },
                            modifier = Modifier.testTag("nav_servers")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.VERSIONS,
                            onClick = { viewModel.navigateTo(LauncherScreen.VERSIONS) },
                            icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Versions") },
                            label = { Text("Versions") },
                            modifier = Modifier.testTag("nav_versions")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.PROFILES,
                            onClick = { viewModel.navigateTo(LauncherScreen.PROFILES) },
                            icon = { Icon(Icons.Default.Build, contentDescription = "Profiles") },
                            label = { Text("Profiles") },
                            modifier = Modifier.testTag("nav_profiles")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.ACCOUNTS,
                            onClick = { viewModel.navigateTo(LauncherScreen.ACCOUNTS) },
                            icon = { Icon(Icons.Default.Person, contentDescription = "Accounts") },
                            label = { Text("Accounts") },
                            modifier = Modifier.testTag("nav_accounts")
                        )
                        NavigationBarItem(
                            selected = currentScreen == LauncherScreen.SETTINGS,
                            onClick = { viewModel.navigateTo(LauncherScreen.SETTINGS) },
                            icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                            label = { Text("Settings") },
                            modifier = Modifier.testTag("nav_settings")
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(
                    androidx.compose.ui.graphics.Brush.verticalGradient(
                        listOf(
                            androidx.compose.material3.MaterialTheme.colorScheme.background,
                            androidx.compose.material3.MaterialTheme.colorScheme.surface,
                            androidx.compose.material3.MaterialTheme.colorScheme.background
                        )
                    )
                )
        ) {
            if (onboardingRequired && !welcomeDismissed) {
                OnboardingScreen(
                    viewModel = viewModel,
                    onContinue = {
                        welcomeDismissed = true
                        viewModel.navigateTo(LauncherScreen.VERSIONS)
                    }
                )
            } else {
                when (currentScreen) {
                    LauncherScreen.HOME -> HomeScreen(viewModel = viewModel)
                    LauncherScreen.VERSIONS -> VersionsScreen(viewModel = viewModel)
                    LauncherScreen.PROFILES -> ProfilesScreen(viewModel = viewModel)
                    LauncherScreen.ACCOUNTS -> AccountsScreen(viewModel = viewModel)
                    LauncherScreen.SETTINGS -> SettingsScreen(viewModel = viewModel)
                    LauncherScreen.LOGS -> LogsScreen(viewModel = viewModel)
                    LauncherScreen.CUSTOMIZE_CONTROLS -> CustomizeControlsScreen(viewModel = viewModel)
                    LauncherScreen.CONTENT -> ContentBrowserScreen(viewModel = viewModel)
                    LauncherScreen.SERVERS -> ServerBrowserScreen(viewModel = viewModel)
                    LauncherScreen.GAME_PLAY -> {}
                }
            }

            if (homeUiState.showRepairDialog) {
                RepairDialog(
                    versionId = homeUiState.selectedVersionId,
                    status = homeUiState.repairStatus,
                    onRepair = { viewModel.performRepair(homeUiState.selectedVersionId) },
                    onDismiss = { viewModel.dismissRepairDialog() }
                )
            }

            if (launchState !is LaunchState.Idle) {
                GameLaunchOverlay(
                    viewModel = viewModel,
                    launchState = launchState
                )
            }
        }
    }
}
