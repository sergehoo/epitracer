import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';

enum AlertLevel { info, warning, critical }

class HealthAlertBanner extends StatelessWidget {
  const HealthAlertBanner({
    super.key,
    required this.title,
    required this.message,
    this.level = AlertLevel.info,
    this.onTap,
  });

  final String title;
  final String message;
  final AlertLevel level;
  final VoidCallback? onTap;

  Gradient _gradient() {
    switch (level) {
      case AlertLevel.critical:
        return AppGradients.sunset;
      case AlertLevel.warning:
        return AppGradients.warmOrange;
      case AlertLevel.info:
        return AppGradients.healthyGreen;
    }
  }

  IconData _icon() {
    switch (level) {
      case AlertLevel.critical:
        return Icons.warning_amber_rounded;
      case AlertLevel.warning:
        return Icons.notification_important_outlined;
      case AlertLevel.info:
        return Icons.info_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: _gradient(),
            borderRadius: BorderRadius.circular(20),
            boxShadow: AppShadows.soft(Colors.black, opacity: 0.2),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.22),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(_icon(), color: Colors.white, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      message,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.9),
                        fontSize: 12,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (onTap != null)
                const Icon(Icons.chevron_right, color: Colors.white),
            ],
          ),
        ),
      ),
    );
  }
}
