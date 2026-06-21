import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/glass_card.dart';
import 'registration_repository.dart';

/// Écran d'enregistrement voyageur : liste les formulaires d'enquête
/// actifs (Ebola, etc.).
///
/// Phase 8B — au clic sur un formulaire, on lance le runner Flutter natif
/// (`/registration/run/:code`) au lieu d'ouvrir le portail web externe.
/// L'option "Ouvrir dans le navigateur" reste dispo en fallback discret
/// au bas de chaque carte au cas où le runner natif aurait un bug.
class RegistrationPickerScreen extends ConsumerWidget {
  const RegistrationPickerScreen({super.key});

  void _openNativeRunner(BuildContext context, RegistrationForm form) {
    // Si pas de code utilisable → fallback ebola par défaut. Le backend a
    // un schéma de secours qui répondra toujours.
    final code = form.code.isEmpty || form.code == 'default'
        ? 'ebola_inhp_v1'
        : form.code;
    context.go('/registration/run/$code');
  }

  Future<void> _openWebFallback(BuildContext context, String url) async {
    if (url.isEmpty) return;
    final uri = Uri.parse(url);
    try {
      final ok =
          await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok) throw 'launchUrl returned false';
    } catch (_) {
      try {
        await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
      } catch (_) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Impossible d\'ouvrir le navigateur. Adresse : $url'),
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(activeFormsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('M\'enregistrer'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(AppRoutes.voyageurLogin),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.neutralLight),
        child: SafeArea(
          child: async.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.cloud_off,
                        size: 64, color: AppColors.slate300),
                    const SizedBox(height: 12),
                    const Text(
                      'Connexion impossible',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Vérifiez votre connexion internet et réessayez.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.slate500),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      onPressed: () => ref.invalidate(activeFormsProvider),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Réessayer'),
                    ),
                  ],
                ),
              ),
            ),
            data: (forms) => ListView(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
              children: [
                // En-tête
                Center(
                  child: Container(
                    height: 64,
                    width: 64,
                    decoration: BoxDecoration(
                      gradient: AppGradients.healthyGreen,
                      borderRadius: BorderRadius.circular(18),
                      boxShadow: AppShadows.elevated(AppColors.ciGreen),
                    ),
                    child: const Icon(Icons.assignment_turned_in,
                        color: Colors.white, size: 32),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Choisissez votre formulaire',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: AppColors.ciDark,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Sélectionnez le formulaire d\'enquête correspondant à votre situation. Le remplissage se fait en ligne, en toute sécurité.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.slate500, fontSize: 13),
                ),
                const SizedBox(height: 24),

                if (forms.isEmpty)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        'Aucun formulaire d\'enquête actif pour le moment.',
                        style: TextStyle(color: AppColors.slate500),
                      ),
                    ),
                  )
                else
                  for (final f in forms) ...[
                    _FormCard(
                      form: f,
                      onTap: () => _openNativeRunner(context, f),
                      onWebFallback: () => _openWebFallback(context, f.webUrl),
                    ),
                    const SizedBox(height: 12),
                  ],

                const SizedBox(height: 24),

                // Étapes explicatives
                _StepsExplainer(),

                const SizedBox(height: 24),

                // Bouton retour login + lien
                Center(
                  child: Column(
                    children: [
                      const Text(
                        'Vous avez déjà rempli votre formulaire ?',
                        style: TextStyle(color: AppColors.slate500, fontSize: 13),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () => context.go(AppRoutes.voyageurLogin),
                        icon: const Icon(Icons.login, size: 16),
                        label: const Text('Me connecter avec mon téléphone'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.ciDark,
                          side: const BorderSide(color: AppColors.ciDark),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 18, vertical: 12),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FormCard extends StatelessWidget {
  const _FormCard({
    required this.form,
    required this.onTap,
    required this.onWebFallback,
  });
  final RegistrationForm form;
  final VoidCallback onTap;
  final VoidCallback onWebFallback;

  Color _color() {
    final code = (form.diseaseCode ?? '').toLowerCase();
    if (code.contains('ebola')) return AppColors.statusDanger;
    if (code.contains('covid')) return AppColors.statusInfo;
    if (code.contains('mpox')) return AppColors.statusWarn;
    if (code.contains('yellow') || code.contains('fievre'))
      return AppColors.ciOrange;
    return AppColors.ciGreen;
  }

  IconData _icon() {
    final code = (form.diseaseCode ?? '').toLowerCase();
    if (code.contains('ebola')) return Icons.coronavirus_outlined;
    if (code.contains('covid')) return Icons.masks_outlined;
    if (code.contains('mpox')) return Icons.healing;
    if (code.contains('yellow') || code.contains('fievre'))
      return Icons.vaccines;
    return Icons.assignment_outlined;
  }

  @override
  Widget build(BuildContext context) {
    final color = _color();
    return GlassCard(
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(_icon(), color: color, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            form.title,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                            ),
                          ),
                        ),
                        if (form.isDefault)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.ciGreen.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Text(
                              'Recommandé',
                              style: TextStyle(
                                color: AppColors.ciGreen,
                                fontSize: 9,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                      ],
                    ),
                    if (form.diseaseName != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        form.diseaseName!,
                        style: TextStyle(
                          color: color,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (form.description.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              form.description,
              style: const TextStyle(
                color: AppColors.slate500,
                fontSize: 12,
                height: 1.4,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.phone_iphone,
                  size: 14, color: AppColors.ciGreen),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'Remplir directement dans l\'application',
                  style: TextStyle(
                    color: AppColors.ciGreen,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Icon(Icons.arrow_forward, size: 18, color: color),
            ],
          ),
          // Fallback discret : ouvrir dans le navigateur en cas de bug runner
          if (form.webUrl.isNotEmpty) ...[
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: onWebFallback,
                icon: const Icon(Icons.open_in_new, size: 12),
                label: const Text(
                  'Ouvrir dans le navigateur',
                  style: TextStyle(fontSize: 10),
                ),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.slate500,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 4, vertical: 0),
                  minimumSize: const Size(0, 24),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StepsExplainer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.ciGreen.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.ciGreen.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Text(
            'Comment ça fonctionne',
            style: TextStyle(
              fontWeight: FontWeight.w800,
              color: AppColors.ciDark,
              fontSize: 13,
            ),
          ),
          SizedBox(height: 10),
          _Step(num: '1', text: 'Choisissez le formulaire correspondant à votre cas'),
          _Step(num: '2', text: 'Remplissez directement dans l\'application (mode hors ligne possible)'),
          _Step(num: '3', text: 'Recevez votre pass sanitaire instantanément'),
          _Step(num: '4', text: 'Conservez votre QR dans l\'app et présentez-le à l\'arrivée'),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.num, required this.text});
  final String num;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 22,
            height: 22,
            decoration: const BoxDecoration(
              color: AppColors.ciGreen,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              num,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 12, color: AppColors.slate700),
            ),
          ),
        ],
      ),
    );
  }
}
