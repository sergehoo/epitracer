import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/router/app_router.dart';
import '../../features/notifications/notifications_repository.dart';
import 'app_bottom_nav.dart';

/// Shell principal qui héberge le dashboard + bottom nav.
/// Pour l'instant on rend le child directement ; ce widget sera étendu
/// pour gérer les routes imbriquées via StatefulShellRoute.
class AppShell extends ConsumerWidget {
  const AppShell({
    super.key,
    required this.currentIndex,
    required this.child,
  });

  final int currentIndex;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(unreadCountProvider);
    return Scaffold(
      extendBody: true,
      body: child,
      bottomNavigationBar: AppBottomNav(
        currentIndex: currentIndex,
        onTap: (i) => _goTo(context, i),
        items: [
          const AppBottomNavItem(
            icon: Icons.home_outlined,
            activeIcon: Icons.home,
            label: 'Accueil',
          ),
          const AppBottomNavItem(
            icon: Icons.qr_code_2_outlined,
            activeIcon: Icons.qr_code_2,
            label: 'Mes pass',
          ),
          const AppBottomNavItem(
            icon: Icons.health_and_safety_outlined,
            activeIcon: Icons.health_and_safety,
            label: 'Santé',
          ),
          const AppBottomNavItem(
            icon: Icons.map_outlined,
            activeIcon: Icons.map,
            label: 'Carte',
          ),
          AppBottomNavItem(
            icon: Icons.person_outline,
            activeIcon: Icons.person,
            label: 'Moi',
            badge: unread > 0 ? unread : null,
          ),
        ],
      ),
    );
  }

  void _goTo(BuildContext context, int i) {
    const routes = [
      AppRoutes.dashboard,
      AppRoutes.passes,
      AppRoutes.followup,
      // Map route ajoutée en Phase 7D — pour l'instant fallback dashboard
      AppRoutes.dashboard,
      AppRoutes.profile,
    ];
    final target = routes[i];
    if (i == 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Carte interactive — Phase 7D 🗺️')),
      );
      return;
    }
    Navigator.of(context).pushReplacementNamed(target);
  }
}
