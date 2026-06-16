import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'animated_counter.dart';
import 'glass_card.dart';

/// KPI card pour le dashboard — icône colorée + nombre animé + label.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
    this.color = AppColors.ciOrange,
    this.suffix = '',
    this.onTap,
    this.trend,
  });

  final IconData icon;
  final num value;
  final String label;
  final String suffix;
  final Color color;
  final VoidCallback? onTap;

  /// Pourcentage d'évolution vs période précédente (+12, -5, etc.).
  final int? trend;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 18),
              ),
              const Spacer(),
              if (trend != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: (trend! >= 0 ? AppColors.statusOk : AppColors.statusDanger)
                        .withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${trend! >= 0 ? "+" : ""}$trend%',
                    style: TextStyle(
                      color: trend! >= 0
                          ? AppColors.statusOk
                          : AppColors.statusDanger,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          AnimatedCounter(
            value: value,
            suffix: suffix,
            style: TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.w800,
              color: color,
              height: 1.0,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(
              color: AppColors.slate500,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
