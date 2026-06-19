import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/i18n/app_i18n.dart' as i18n;
import '../../core/i18n/app_i18n.dart';
import '../../core/router/app_router.dart';
import '../../core/security/biometric_service.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/afriq_credit_footer.dart';

/// Écran Paramètres consolidé : langue, biométrie, notifications, à propos.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(localeProvider);
    final t = ref.watch(translateProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('settings.title'))),
      body: ListView(
        children: [
          const _SectionHeader(label: 'Langue'),
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Column(
              children: AppI18n.supportedLanguages.entries.map((e) {
                final disabled = e.key == AppI18n.dyu || e.key == AppI18n.bci;
                return RadioListTile<String>(
                  value: e.key,
                  groupValue: locale,
                  onChanged: disabled
                      ? null
                      : (v) {
                          if (v != null) {
                            i18n.setLocale(ref, v);
                          }
                        },
                  title: Text(e.value),
                  subtitle: disabled
                      ? const Text(
                          'Bientôt disponible',
                          style: TextStyle(
                              fontSize: 11, color: AppColors.slate500),
                        )
                      : null,
                  activeColor: AppColors.ciOrange,
                  dense: true,
                );
              }).toList(),
            ),
          ),

          const _SectionHeader(label: 'Sécurité'),
          _BiometricToggle(),

          const _SectionHeader(label: 'Notifications'),
          const ListTile(
            leading: Icon(Icons.notifications_outlined),
            title: Text('Préférences notifications'),
            subtitle: Text(
              'Géré par votre système — Réglages → Notifications',
              style: TextStyle(fontSize: 11),
            ),
          ),

          const _SectionHeader(label: 'Aide & informations'),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: Text(t('settings.about')),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRoutes.about),
          ),
          ListTile(
            leading: const Icon(Icons.shield_outlined),
            title: const Text('Politique de confidentialité'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              final uri = Uri.parse('https://veillesanitaire.com/privacy');
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            },
          ),
          ListTile(
            leading: const Icon(Icons.help_outline),
            title: const Text('Aide & FAQ'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              final uri = Uri.parse('https://veillesanitaire.com/aide');
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            },
          ),

          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: AppColors.statusDanger),
            title: Text(
              t('settings.logout'),
              style: const TextStyle(color: AppColors.statusDanger),
            ),
            onTap: () async {
              await ref.read(secureStorageProvider).clearSession();
              if (context.mounted) context.go(AppRoutes.voyageurLogin);
            },
          ),
          const SizedBox(height: 16),
          const Divider(color: AppColors.slate200, height: 1),
          const AfriqCreditFooter(),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 16, 6),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w800,
          color: AppColors.slate500,
          letterSpacing: 1.5,
        ),
      ),
    );
  }
}

/// Toggle biométrie (réutilisé depuis profile_screen mais isolé ici).
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
      final ok = await svc.authenticate(
          reason: 'Activez le verrouillage biométrique');
      if (!ok) return;
    }
    await svc.setEnabled(v);
    if (!mounted) return;
    setState(() => _enabled = v);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const SizedBox(height: 56);
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
        "Face ID / empreinte à chaque ouverture",
        style: TextStyle(fontSize: 11),
      ),
      value: _enabled,
      onChanged: _toggle,
      activeColor: AppColors.ciOrange,
    );
  }
}
