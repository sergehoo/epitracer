import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Palette de gradients officielle Mon Pass Sanitaire — édition épurée.
/// Pas de violet, pas de bleu vif, pas de rose : uniquement CI orange/vert,
/// dégradés sombres pour profondeur, et neutres.
class AppGradients {
  AppGradients._();

  // ─── Hero principal — vert institutionnel CI ────────────────────
  static const LinearGradient healthyGreen = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF064E3B), Color(0xFF007A45), Color(0xFF10B981)],
    stops: [0.0, 0.55, 1.0],
  );

  // ─── Hero secondaire — orange CI (cards alerte douce) ───────────
  static const LinearGradient warmOrange = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFC2410C), Color(0xFFF77F00), Color(0xFFFFB74D)],
  );

  // ─── Bicolore CI (orange → vert) — utilisé avec parcimonie ──────
  static const LinearGradient ciFlag = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [AppColors.ciOrange, Color(0xFFE8E8E5), AppColors.ciGreen],
    stops: [0.0, 0.5, 1.0],
  );

  // ─── Dark mode + splash ─────────────────────────────────────────
  static const LinearGradient nightDark = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0A1410), Color(0xFF11221A), Color(0xFF1A3A2A)],
  );

  // ─── Neutre clair — fond dashboard / onboarding ─────────────────
  static const LinearGradient neutralLight = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFAFAF7), Color(0xFFF1F4F0), Color(0xFFE8EDE8)],
  );

  // ─── Critique (alerte sanitaire grave uniquement) ───────────────
  static const LinearGradient critical = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF7F1D1D), Color(0xFFB91C1C), Color(0xFFDC2626)],
  );

  /// Glass overlay — appliqué sur cards en glassmorphism
  static LinearGradient glass({double opacity = 0.18}) => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withValues(alpha: opacity),
          Colors.white.withValues(alpha: opacity * 0.4),
        ],
      );

  // Alias rétrocompat (pour pages stories qui en dépendaient)
  static const LinearGradient sunset = warmOrange;
  static const LinearGradient aurora = neutralLight;
}

/// Ombres standardisées
class AppShadows {
  AppShadows._();

  static List<BoxShadow> soft(Color tint, {double opacity = 0.12}) => [
        BoxShadow(
          color: tint.withValues(alpha: opacity),
          blurRadius: 24,
          offset: const Offset(0, 8),
          spreadRadius: -4,
        ),
      ];

  static List<BoxShadow> elevated(Color tint, {double opacity = 0.2}) => [
        BoxShadow(
          color: tint.withValues(alpha: opacity),
          blurRadius: 40,
          offset: const Offset(0, 16),
          spreadRadius: -8,
        ),
      ];

  static const List<BoxShadow> card = [
    BoxShadow(
      color: Color(0x0A000000),
      blurRadius: 20,
      offset: Offset(0, 4),
      spreadRadius: 0,
    ),
  ];
}
