import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';

/// Card en glassmorphism — fond blanchi + flou backdrop + bordure subtile.
/// Utilisée pour les KPI dashboards, sélecteurs membres famille, etc.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.borderRadius = 24,
    this.tint,
    this.blur = 12,
    this.borderColor,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double borderRadius;
  final Color? tint;
  final double blur;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final effectiveTint = tint ??
        (isDark
            ? AppColors.darkCard.withValues(alpha: 0.55)
            : Colors.white.withValues(alpha: 0.65));

    final card = ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          decoration: BoxDecoration(
            color: effectiveTint,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: borderColor ??
                  (isDark
                      ? Colors.white.withValues(alpha: 0.08)
                      : Colors.white.withValues(alpha: 0.5)),
              width: 1,
            ),
            gradient: AppGradients.glass(opacity: isDark ? 0.05 : 0.25),
            boxShadow: AppShadows.card,
          ),
          padding: padding,
          child: child,
        ),
      ),
    );

    if (onTap == null) return card;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(borderRadius),
        onTap: onTap,
        child: card,
      ),
    );
  }
}
