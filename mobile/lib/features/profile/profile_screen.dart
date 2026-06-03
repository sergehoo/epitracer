import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profil & paramètres')),
      body: ListView(
        children: [
          const SizedBox(height: 16),
          Center(
            child: CircleAvatar(
              radius: 44,
              backgroundColor: AppColors.ciOrange.withValues(alpha: 0.1),
              child: const Icon(Icons.person,
                  size: 48, color: AppColors.ciOrange),
            ),
          ),
          const SizedBox(height: 24),
          const ListTile(
            leading: Icon(Icons.lock_outline),
            title: Text('Sécurité & authentification'),
            trailing: Icon(Icons.chevron_right),
          ),
          const ListTile(
            leading: Icon(Icons.fingerprint),
            title: Text('Verrouillage biométrique'),
            trailing: Icon(Icons.chevron_right),
          ),
          const ListTile(
            leading: Icon(Icons.notifications_outlined),
            title: Text('Préférences notifications'),
            trailing: Icon(Icons.chevron_right),
          ),
          const ListTile(
            leading: Icon(Icons.location_on_outlined),
            title: Text('Partage de position'),
            trailing: Icon(Icons.chevron_right),
          ),
          const ListTile(
            leading: Icon(Icons.shield_outlined),
            title: Text('Mes données & confidentialité'),
            trailing: Icon(Icons.chevron_right),
          ),
          const ListTile(
            leading: Icon(Icons.help_outline),
            title: Text('Aide et FAQ'),
            trailing: Icon(Icons.chevron_right),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: AppColors.statusDanger),
            title: const Text('Se déconnecter',
                style: TextStyle(color: AppColors.statusDanger)),
            onTap: () async {
              await ref.read(secureStorageProvider).clearSession();
              if (context.mounted) context.go(AppRoutes.login);
            },
          ),
          const SizedBox(height: 16),
          Center(
            child: Text(
              'Mon Pass Sanitaire v1.0.0\nINHP · MSHPCMU · République de Côte d\'Ivoire',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade500,
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
