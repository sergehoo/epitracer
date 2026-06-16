import 'package:flutter/material.dart';

import 'app_colors.dart';

class AppTheme {
  static const String fontFamily = 'Inter';

  // ── LIGHT ──────────────────────────────────────────────────────────
  static ThemeData light() {
    final base = ThemeData.light(useMaterial3: true);
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.ciOrange,
      primary: AppColors.ciOrange,
      secondary: AppColors.ciGreen,
      tertiary: AppColors.ciDark,
      surface: Colors.white,
      onSurface: AppColors.slate900,
      brightness: Brightness.light,
    );
    return base.copyWith(
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.slate50,
      textTheme: _textTheme(base.textTheme, AppColors.slate900),
      cardTheme: _cardTheme(Colors.white),
      appBarTheme: _appBarTheme(Colors.white, AppColors.slate900),
      elevatedButtonTheme: _elevatedBtn(scheme),
      filledButtonTheme: _filledBtn(scheme),
      outlinedButtonTheme: _outlinedBtn(scheme),
      textButtonTheme: _textBtn(scheme),
      inputDecorationTheme: _inputDecoration(
        fill: Colors.white,
        border: AppColors.slate200,
      ),
      dividerColor: AppColors.slate200,
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: AppColors.ciOrange,
        unselectedItemColor: AppColors.slate500,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }

  // ── DARK ───────────────────────────────────────────────────────────
  static ThemeData dark() {
    final base = ThemeData.dark(useMaterial3: true);
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.ciOrange,
      primary: AppColors.ciOrangeLight,
      secondary: AppColors.ciGreenLight,
      tertiary: AppColors.ciDark,
      surface: AppColors.darkCard,
      onSurface: AppColors.slate100,
      brightness: Brightness.dark,
    );
    return base.copyWith(
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.darkBg,
      textTheme: _textTheme(base.textTheme, AppColors.slate100),
      cardTheme: _cardTheme(AppColors.darkCard),
      appBarTheme: _appBarTheme(AppColors.darkBg, AppColors.slate100),
      elevatedButtonTheme: _elevatedBtn(scheme),
      filledButtonTheme: _filledBtn(scheme),
      outlinedButtonTheme: _outlinedBtn(scheme),
      textButtonTheme: _textBtn(scheme),
      inputDecorationTheme: _inputDecoration(
        fill: AppColors.darkCard,
        border: AppColors.darkBorder,
      ),
      dividerColor: AppColors.darkBorder,
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.darkCard,
        selectedItemColor: AppColors.ciOrangeLight,
        unselectedItemColor: AppColors.slate500,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }

  // ── Builders communs ───────────────────────────────────────────────
  static TextTheme _textTheme(TextTheme base, Color color) {
    return base.apply(fontFamily: fontFamily, bodyColor: color, displayColor: color).copyWith(
      displayLarge: base.displayLarge?.copyWith(fontWeight: FontWeight.w800, height: 1.1),
      headlineLarge: base.headlineLarge?.copyWith(fontWeight: FontWeight.w800),
      headlineMedium: base.headlineMedium?.copyWith(fontWeight: FontWeight.w700),
      titleLarge: base.titleLarge?.copyWith(fontWeight: FontWeight.w700),
      titleMedium: base.titleMedium?.copyWith(fontWeight: FontWeight.w600),
      bodyLarge: base.bodyLarge?.copyWith(height: 1.5),
      bodyMedium: base.bodyMedium?.copyWith(height: 1.5),
      labelLarge: base.labelLarge?.copyWith(fontWeight: FontWeight.w600, letterSpacing: 0.3),
    );
  }

  static CardThemeData _cardTheme(Color fill) => CardThemeData(
        color: fill,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: fill == Colors.white ? AppColors.slate200 : AppColors.darkBorder),
        ),
      );

  static AppBarTheme _appBarTheme(Color bg, Color fg) => AppBarTheme(
        backgroundColor: bg,
        foregroundColor: fg,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w700,
          fontSize: 18,
          color: fg,
        ),
      );

  static ElevatedButtonThemeData _elevatedBtn(ColorScheme s) => ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: s.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      );

  static FilledButtonThemeData _filledBtn(ColorScheme s) => FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      );

  static OutlinedButtonThemeData _outlinedBtn(ColorScheme s) => OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: s.primary,
          side: BorderSide(color: s.primary, width: 1.4),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
          textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      );

  static TextButtonThemeData _textBtn(ColorScheme s) => TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: s.primary,
          textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w600),
        ),
      );

  static InputDecorationTheme _inputDecoration({
    required Color fill,
    required Color border,
  }) =>
      InputDecorationTheme(
        filled: true,
        fillColor: fill,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.ciOrange, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.statusDanger),
        ),
      );
}
