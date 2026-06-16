import 'package:flutter/material.dart';

/// Palette officielle Côte d'Ivoire — Mon Pass Sanitaire.
///
/// Orange + Vert + Blanc des armoiries, déclinés en tokens utilisables
/// dans tout l'app via [AppColors.of(context)].
class AppColors {
  // ── Couleurs institutionnelles ─────────────────────────────────────
  static const Color ciOrange = Color(0xFFF77F00);
  static const Color ciGreen = Color(0xFF009B5A);
  static const Color ciDark = Color(0xFF064E3B);
  static const Color ciOrangeLight = Color(0xFFFFA94D);
  static const Color ciGreenLight = Color(0xFF34D399);

  // ── INHP institutionnel (badges admin/staff) ───────────────────────
  static const Color inhpBlue = Color(0xFF1E40AF);

  // ── Statuts sanitaires ─────────────────────────────────────────────
  static const Color statusOk = Color(0xFF10B981);      // pass valide / sain
  static const Color statusWarn = Color(0xFFF59E0B);    // bientôt expiré / vigilance
  static const Color statusDanger = Color(0xFFEF4444);  // expiré / symptôme grave
  static const Color statusError = statusDanger;        // alias rétro-compat
  static const Color statusInfo = Color(0xFF0EA5E9);    // notification

  // ── Neutres ────────────────────────────────────────────────────────
  static const Color slate50 = Color(0xFFF8FAFC);
  static const Color slate100 = Color(0xFFF1F5F9);
  static const Color slate200 = Color(0xFFE2E8F0);
  static const Color slate300 = Color(0xFFCBD5E1);
  static const Color slate500 = Color(0xFF64748B);
  static const Color slate700 = Color(0xFF334155);
  static const Color slate900 = Color(0xFF0F172A);

  // ── Surfaces dark mode ─────────────────────────────────────────────
  static const Color darkBg = Color(0xFF0A0F0D);
  static const Color darkCard = Color(0xFF111A17);
  static const Color darkBorder = Color(0xFF1F2A26);
}
