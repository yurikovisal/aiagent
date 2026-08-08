import 'package:flutter/material.dart';

class MezaTheme {
  static const forest = Color(0xFF1F3D2A);
  static const copper = Color(0xFFC56A2D);
  static const mist = Color(0xFFE8EFE9);
  static const ink = Color(0xFF142018);

  static ThemeData get light {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: forest,
        primary: forest,
        secondary: copper,
        surface: mist,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: mist,
      fontFamily: 'Roboto',
    );
    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: forest,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: copper,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
    );
  }
}
