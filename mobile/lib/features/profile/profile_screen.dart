import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/security/biometric_service.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import 'profile_repository.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider).asData?.value;
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
          const SizedBox(height: 12),
          Center(
            child: Text(
              profile?.fullName.isNotEmpty == true
                  ? profile!.fullName
                  : 'Voyageur',
              style: const TextStyle(
                  fontSize: 18, fontWeight: FontWeight.w700),
            ),
          ),
          if (profile?.email.isNotEmpty == true)
            Center(
              child: Text(
                profile!.email,
                style: const TextStyle(color: AppColors.slate500),
              ),
            ),
          const SizedBox(height: 24),
          const ListTile(
            leading: Icon(Icons.lock_outline),
            title: Text('Sécurité & authentification'),
            trailing: Icon(Icons.chevron_right),
          ),
          _BiometricToggle(),
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

/// Toggle ON/OFF du verrouillage biométrique, avec contrôle de support
/// device et confirmation par auth avant activation.
class _BiometricToggle extends ConsumerStatefulWidget {
  @override
  ConsumerState<_BiometricToggle> createState() => _BiometricToggleState();
}

class _BiometricToggleState extends ConsumerState<_BiometricToggle> {
  bool _enabled = false;
  bool _supported = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final svc = ref.read(biometricServiceProvider);
    final supported = await svc.canUseBiometrics();
    final enabled = await svc.isEnabled();
    if (!mounted) return;
    setState(() {
      _supported = supported;
      _enabled = enabled;
      _loading = false;
    });
  }

  Future<void> _toggle(bool v) async {
    final svc = ref.read(biometricServiceProvider);
    if (v) {
      // Demande l'auth avant d'activer pour s'assurer qu'elle marche
      final ok = await svc.authenticate(
          reason: 'Activez le verrouillage biométrique');
      if (!ok) return;
    }
    await svc.setEnabled(v);
    if (!mounted) return;
    setState(() => _enabled = v);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(v
          ? 'Verrouillage biométrique activé'
          : 'Verrouillage biométrique désactivé'),
    ));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const ListTile(
        leading: Icon(Icons.fingerprint),
        title: Text('Verrouillage biométrique'),
        trailing: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }
    if (!_supported) {
      return const ListTile(
        leading: Icon(Icons.fingerprint, color: AppColors.slate300),
        title: Text('Verrouillage biométrique'),
        subtitle: Text('Non disponible sur cet appareil'),
      );
    }
    return SwitchListTile(
      secondary: const Icon(Icons.fingerprint),
      title: const Text('Verrouillage biométrique'),
      subtitle: const Text(
          "Face ID / empreinte / code d'écran à chaque ouverture"),
      value: _enabled,
      onChanged: _toggle,
      activeColor: AppColors.ciOrange,
    );
  }
}
