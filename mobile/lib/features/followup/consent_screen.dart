import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import 'followup_repository.dart';
import 'location_ping_service.dart';

/// Écran "Consentement RGPD" — toggle géolocalisation + texte légal complet.
///
/// Aligné avec l'expérience PWA (carte "Partager ma position" dans la
/// sidebar de /voyageur/suivi). Côté mobile, l'enjeu est plus fort car
/// la géolocalisation tourne en arrière-plan ; on insiste sur la
/// finalité, la révocabilité et la base légale.
class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({super.key});

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {
  bool _geoConsent = false;
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final repo = ref.read(followupRepositoryProvider);
    final status = await repo.fetchFollowUpStatus();
    if (!mounted) return;
    setState(() {
      _geoConsent = status?.geolocationConsented ?? false;
      _loading = false;
    });
  }

  Future<void> _toggleGeo(bool nextValue) async {
    setState(() => _saving = true);
    final repo = ref.read(followupRepositoryProvider);
    final ok = await repo.recordConsent(
      scope: 'geolocation',
      granted: nextValue,
      textExcerpt: nextValue
          ? "J'autorise le partage de ma position lors des check-ins et des demandes d'assistance."
          : "Je retire mon autorisation de partage de position.",
      revocationReason:
          nextValue ? '' : "Retrait par l'utilisateur depuis l'app mobile.",
    );
    if (!mounted) return;
    if (ok) {
      setState(() {
        _geoConsent = nextValue;
        _saving = false;
      });
      // Démarrer / arrêter le service de ping en conséquence
      final pingSvc = ref.read(locationPingServiceProvider);
      if (nextValue) {
        await pingSvc.start();
      } else {
        await pingSvc.stop();
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            nextValue
                ? 'Merci. Vous pourrez être orienté plus rapidement en cas de besoin.'
                : "C'est noté. Aucune position ne sera collectée.",
          ),
          backgroundColor:
              nextValue ? AppColors.statusOk : AppColors.slate500,
        ),
      );
      // Rafraîchir l'état du suivi
      ref.invalidate(followUpStatusProvider);
    } else {
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content:
              Text("Impossible d'enregistrer votre choix pour le moment."),
          backgroundColor: AppColors.statusDanger,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Confidentialité')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // ── Toggle principal ─────────────────────────────────
                Container(
                  decoration: BoxDecoration(
                    color: AppColors.ciGreen.withValues(alpha: 0.06),
                    border: Border.all(
                      color: AppColors.ciGreen.withValues(alpha: 0.25),
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.location_on_outlined,
                              color: AppColors.ciGreen),
                          const SizedBox(width: 8),
                          const Expanded(
                            child: Text(
                              'Partager ma position',
                              style: TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          Switch.adaptive(
                            value: _geoConsent,
                            onChanged:
                                _saving ? null : (v) => _toggleGeo(v),
                            activeColor: AppColors.ciGreen,
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        "J'autorise le partage de ma position lors des check-ins "
                        "et des demandes d'assistance. Tant que cette option est "
                        "activée, l'application enverra discrètement un signal "
                        "de position toutes les 4 heures pour permettre aux "
                        "équipes sanitaires de m'orienter plus rapidement.",
                        style: TextStyle(
                          color: AppColors.slate700,
                          height: 1.4,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // ── Texte légal ──────────────────────────────────────
                const Text(
                  "Ce que cela signifie",
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 10),
                const _LegalBlock(
                  icon: Icons.medical_information_outlined,
                  title: 'Finalité',
                  body:
                      "Vos coordonnées GPS servent uniquement à orienter une "
                      "équipe sanitaire en cas de symptôme ou de demande d'aide. "
                      "Elles ne sont jamais utilisées à des fins publicitaires "
                      "ni partagées avec des tiers commerciaux.",
                ),
                const _LegalBlock(
                  icon: Icons.gavel_outlined,
                  title: 'Base légale',
                  body:
                      "Loi ivoirienne n° 2013-450 sur la protection des "
                      "données à caractère personnel. Le traitement repose "
                      "exclusivement sur votre consentement explicite.",
                ),
                const _LegalBlock(
                  icon: Icons.timer_outlined,
                  title: 'Durée de conservation',
                  body:
                      "Les positions sont conservées au maximum 90 jours, "
                      "puis purgées automatiquement. Vous pouvez à tout moment "
                      "demander leur suppression anticipée depuis la rubrique "
                      "Mes données.",
                ),
                const _LegalBlock(
                  icon: Icons.lock_outline,
                  title: 'Accès aux données',
                  body:
                      "Seuls les agents INHP affectés à votre suivi peuvent "
                      "consulter votre position. Chaque accès est journalisé "
                      "et auditable.",
                ),
                const _LegalBlock(
                  icon: Icons.cancel_outlined,
                  title: 'Retrait à tout moment',
                  body:
                      "Vous pouvez désactiver le partage en un toucher. Le "
                      "retrait est effectif immédiatement et n'entraîne aucune "
                      "conséquence sur votre prise en charge sanitaire.",
                ),
                const SizedBox(height: 24),
                Center(
                  child: Text(
                    'Politique de confidentialité $kConsentVersion',
                    style: const TextStyle(
                      color: AppColors.slate500,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
    );
  }
}

class _LegalBlock extends StatelessWidget {
  const _LegalBlock({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.ciGreen.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: AppColors.ciGreen, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: const TextStyle(
                    color: AppColors.slate700,
                    height: 1.4,
                    fontSize: 12.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
