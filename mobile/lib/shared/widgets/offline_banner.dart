import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/connectivity_service.dart';
import '../../core/theme/app_colors.dart';

/// Bandeau qui s'affiche en haut de l'écran quand l'appareil est hors-ligne.
/// À placer dans un Scaffold via la propriété [Scaffold.bottomNavigationBar]
/// ou via un wrapper d'écran.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final online = ref.watch(isOnlineProvider).asData?.value ?? true;
    if (online) return const SizedBox.shrink();

    return Material(
      color: AppColors.statusWarn,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: const [
              Icon(Icons.wifi_off, color: Colors.white, size: 18),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Mode hors-ligne — vos données seront synchronisées au retour de la connexion',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Wrapper qui ajoute automatiquement l'OfflineBanner en haut de child.
class WithOfflineBanner extends StatelessWidget {
  const WithOfflineBanner({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const OfflineBanner(),
        Expanded(child: child),
      ],
    );
  }
}
