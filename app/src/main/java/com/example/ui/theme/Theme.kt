package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val DarkColorScheme = darkColorScheme(
    primary = GrassGreenLight,
    onPrimary = Color(0xFF061009),
    primaryContainer = Color(0xFF174D26),
    onPrimaryContainer = Color(0xFFD5FFDA),
    secondary = DiamondCyan,
    onSecondary = Color(0xFF001F22),
    secondaryContainer = Color(0xFF0D4148),
    onSecondaryContainer = Color(0xFFB8F7FC),
    tertiary = GoldYellow,
    background = DarkCanvas,
    onBackground = TextPrimary,
    surface = DarkSurface,
    onSurface = TextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = TextSecondary,
    outline = Color(0xFF39464D),
    outlineVariant = Color(0xFF273239),
    error = RedstoneRed,
    onError = Color.White
)

private val LightColorScheme = lightColorScheme(
    primary = GrassGreenDark,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD7F7DA),
    onPrimaryContainer = Color(0xFF05210A),
    secondary = Color(0xFF006874),
    onSecondary = Color.White,
    tertiary = Color(0xFF7A5B00),
    background = Color(0xFFF5F8F5),
    onBackground = Color(0xFF131A15),
    surface = Color(0xFFF8FAF8),
    onSurface = Color(0xFF131A15),
    surfaceVariant = Color(0xFFE5ECE6),
    onSurfaceVariant = Color(0xFF4B5750),
    outline = Color(0xFF78837C),
    outlineVariant = Color(0xFFD0D8D1),
    error = Color(0xFFBA1A1A)
)

private val CraftTypography = Typography(
    displayLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Black, fontSize = 40.sp, lineHeight = 44.sp),
    displaySmall = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Black, fontSize = 34.sp, lineHeight = 38.sp),
    headlineLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Black, fontSize = 30.sp, lineHeight = 34.sp),
    headlineMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.ExtraBold, fontSize = 25.sp, lineHeight = 30.sp),
    headlineSmall = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp, lineHeight = 27.sp),
    titleLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 25.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 16.sp, lineHeight = 21.sp),
    bodyLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 12.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 14.sp, lineHeight = 18.sp),
    labelMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 0.7.sp),
    labelSmall = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.SemiBold, fontSize = 10.sp, letterSpacing = 0.8.sp)
)

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = true,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    MaterialTheme(colorScheme = colorScheme, typography = CraftTypography, content = content)
}
