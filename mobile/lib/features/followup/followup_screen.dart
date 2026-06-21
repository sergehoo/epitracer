import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/followup_chart.dart';
import '../../shared/widgets/offline_banner.dart';
import 'followup_repository.dart';
import 'location_ping_service.dart';

/// Écran principal du suivi 21 jours — parité PWA /voyageur/suivi.
///
/// Affiche :
///   • Compteur grand "Jour X / 21" + barre de progression
///   • Bandeau rouge si symptôme critique récent
///   • Bouton "Faire mon check-in du jour" (état actif / déjà fait)
///   • Mini-graphe `FollowupChart` des 21 jours
///   • Liste des 7 derniers check-ins
///   • Accès rapide consentement RGPD
///   • Numéros d'urgence (samu / allô santé / secours)
class FollowupScreen extends ConsumerStatefulWidget {
  const FollowupScreen({super.key});

  @override
  ConsumerState<FollowupScreen> createState() => _FollowupScreenState();
}

class _FollowupScreenState extends ConsumerState<FollowupScreen> {
  @override
  void initState() {
    super.initState();
    // Démarrage différé du service de pings : la première lecture du
    // statut détermine si le consentement géoloc est actif.
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final status =
          await ref.read(followupRepositoryProvider).fetchFollowUpStatus();
      if (status?.geolocationConsented == true && mounted) {
        await ref.read(locationPingServiceProvider).start();
      }
    });
  }

  Future<void> _callAssistance(String number) async {
    final uri = Uri(scheme: 'tel', path: number);
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Composez $number depuis votre téléphone.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(followUpStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Suivi sanitaire'),
        actions: [
          IconButton(
            tooltip: 'Confidentialité',
            icon: const Icon(Icons.privacy_tip_outlined),
            onPressed: () => context.push(AppRoutes.consent),
          ),
        ],
      ),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => _FallbackToSummary(error: e),
              data: (status) {
                if (status == null) {
                  return const _FallbackToSummary();
                }
                if (!status.active) {
                  return const _InactiveState();
                }
                return RefreshIndicator(
                  onRefresh: () async {
                    ref.invalidate(followUpStatusProvider);
                  },
                  child: ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      _DayHeader(status: status),
                      const SizedBox(height: 16),

                      // Bandeau critique persistant si dernier check-in critique
                      if (status.hasCriticalRecentSymptom) ...[
                        _CriticalAlertBanner(
                          onCallTap: () => _callAssistance(status.alloSante),
                          number: status.alloSante,
                        ),
                        const SizedBox(height: 16),
                      ],

                      _CheckinCta(status: status),
                      const SizedBox(height: 20),

                      // Graphique évolution (parité fl_chart)
                      FollowupChart(
                        currentDay: status.currentDay,
                        totalDays: status.totalDaysDisplay,
                        completedDays: status.checks
                            .map((c) => c.dayIndex + 1)
                            .toList(growable: false),
                      ),
                      const SizedBox(height: 20),

                      _HistorySection(checks: status.checks),

                      const SizedBox(height: 20),
                      _PrivacyCard(
                        geoConsented: status.geolocationConsented,
                        onTap: () => context.push(AppRoutes.consent),
                      ),

                      const SizedBox(height: 20),
                      _AssistanceCard(
                        status: status,
                        onCall: _callAssistance,
                      ),
                      const SizedBox(height: 24),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// ============================================================================
/// Blocs UI
/// ============================================================================

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.status});
  final FollowUpStatus status;

  @override
  Widget build(BuildContext context) {
    final day = status.currentDay;
    final total = status.totalDaysDisplay;
    final ratio = total == 0 ? 0.0 : (day / total).clamp(0.0, 1.0);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.ciOrange, AppColors.ciGreen],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.ciGreen.withValues(alpha: 0.25),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'Jour $day',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 40,
                  fontWeight: FontWeight.w900,
                  height: 1,
                ),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  '/ $total',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: ratio,
              backgroundColor: Colors.white24,
              valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
              minHeight: 10,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            status.daysRemaining > 0
                ? 'Encore ${status.daysRemaining} ${status.daysRemaining == 1 ? "jour" : "jours"} de suivi sanitaire'
                : 'Suivi terminé — merci de votre coopération !',
            style: const TextStyle(color: Colors.white, fontSize: 13),
          ),
          if (status.fullName.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              status.fullName,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.85),
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _CheckinCta extends StatelessWidget {
  const _CheckinCta({required this.status});
  final FollowUpStatus status;

  bool get _doneToday {
    final last = status.lastCheck;
    if (last == null) return false;
    final today = DateTime.now();
    return last.checkDate.year == today.year &&
        last.checkDate.month == today.month &&
        last.checkDate.day == today.day;
  }

  @override
  Widget build(BuildContext context) {
    if (_doneToday) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.statusOk.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: AppColors.statusOk.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle, color: AppColors.statusOk),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Check-in du jour validé. Merci !',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: AppColors.statusOk,
                ),
              ),
            ),
            TextButton(
              onPressed: () => context.push(AppRoutes.checkin),
              child: const Text('Modifier'),
            ),
          ],
        ),
      );
    }
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () => context.push(AppRoutes.checkin),
        icon: const Icon(Icons.health_and_safety),
        label: const Text('Faire mon check-in du jour'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 16),
        ),
      ),
    );
  }
}

class _CriticalAlertBanner extends StatelessWidget {
  const _CriticalAlertBanner({
    required this.number,
    required this.onCallTap,
  });
  final String number;
  final VoidCallback onCallTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.statusDanger, Color(0xFFB91C1C)],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AppColors.statusDanger.withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.warning_amber_rounded,
                color: Colors.white, size: 28),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Symptôme à surveiller',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  "Contactez immédiatement le 143 (Allô Santé).",
                  style: TextStyle(color: Colors.white, fontSize: 12.5),
                ),
              ],
            ),
          ),
          ElevatedButton.icon(
            onPressed: onCallTap,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: AppColors.statusDanger,
              padding: const EdgeInsets.symmetric(horizontal: 12),
            ),
            icon: const Icon(Icons.call),
            label: Text(number,
                style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }
}

class _HistorySection extends StatelessWidget {
  const _HistorySection({required this.checks});
  final List<CheckEntry> checks;

  @override
  Widget build(BuildContext context) {
    final last7 = checks.take(7).toList();
    if (last7.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.slate100,
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Row(
          children: [
            Icon(Icons.history, color: AppColors.slate500),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                "Aucun check-in encore. Faites le premier dès maintenant !",
                style: TextStyle(color: AppColors.slate500, fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }
    final df = DateFormat('EEE d MMM', 'fr_FR');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 4),
          child: Text(
            'Mes 7 derniers check-ins',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
          ),
        ),
        const SizedBox(height: 8),
        for (final c in last7) _HistoryRow(check: c, dateFmt: df),
      ],
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.check, required this.dateFmt});
  final CheckEntry check;
  final DateFormat dateFmt;

  Color get _statusColor {
    if (check.alertRaised || check.hasCriticalSymptom) {
      return AppColors.statusDanger;
    }
    if (check.hasSymptoms) return AppColors.statusWarn;
    return AppColors.statusOk;
  }

  IconData get _statusIcon {
    if (check.alertRaised || check.hasCriticalSymptom) {
      return Icons.warning_amber_rounded;
    }
    if (check.hasSymptoms) return Icons.health_and_safety_outlined;
    return Icons.check_circle_outline;
  }

  String get _statusLabel {
    if (check.alertRaised || check.hasCriticalSymptom) {
      return 'À surveiller';
    }
    if (check.hasSymptoms) return 'Symptômes signalés';
    return 'Tout va bien';
  }

  @override
  Widget build(BuildContext context) {
    final temp = check.temperatureCelsius;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: _statusColor.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _statusColor.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(_statusIcon, color: _statusColor),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'J${check.dayIndex + 1} · ${dateFmt.format(check.checkDate)}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                    if (temp != null) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppColors.slate200),
                        ),
                        child: Text(
                          '${temp.toStringAsFixed(1)} °C',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  _statusLabel,
                  style: TextStyle(color: _statusColor, fontSize: 12),
                ),
                if (check.positiveSymptoms.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      check.positiveSymptoms.length == 1
                          ? '1 symptôme'
                          : '${check.positiveSymptoms.length} symptômes',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.slate500,
                      ),
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

class _PrivacyCard extends StatelessWidget {
  const _PrivacyCard({required this.geoConsented, required this.onTap});
  final bool geoConsented;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = geoConsented ? AppColors.ciGreen : AppColors.slate500;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.slate200),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              Icon(
                geoConsented
                    ? Icons.location_on_outlined
                    : Icons.location_off_outlined,
                color: color,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Partage de position',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    Text(
                      geoConsented
                          ? 'Activé — un signal toutes les 4 h'
                          : 'Désactivé',
                      style: TextStyle(color: color, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: color),
            ],
          ),
        ),
      ),
    );
  }
}

class _AssistanceCard extends StatelessWidget {
  const _AssistanceCard({required this.status, required this.onCall});
  final FollowUpStatus status;
  final void Function(String) onCall;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.statusDanger.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppColors.statusDanger.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "En cas d'urgence",
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
          ),
          const SizedBox(height: 8),
          _EmergencyRow(
            label: 'Allô Santé',
            number: status.alloSante,
            onCall: onCall,
          ),
          _EmergencyRow(
            label: 'SAMU',
            number: status.samu,
            onCall: onCall,
          ),
          _EmergencyRow(
            label: 'Secours',
            number: status.secours,
            onCall: onCall,
          ),
        ],
      ),
    );
  }
}

class _EmergencyRow extends StatelessWidget {
  const _EmergencyRow({
    required this.label,
    required this.number,
    required this.onCall,
  });
  final String label;
  final String number;
  final void Function(String) onCall;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
          TextButton.icon(
            onPressed: () => onCall(number),
            icon: const Icon(Icons.call, size: 16),
            label: Text(
              number,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.ciOrange,
            ),
          ),
        ],
      ),
    );
  }
}

class _InactiveState extends StatelessWidget {
  const _InactiveState();
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.favorite_border,
                size: 72, color: AppColors.slate300),
            SizedBox(height: 12),
            Text(
              'Aucun suivi en cours',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
            SizedBox(height: 6),
            Text(
              "Le suivi 21 jours s'active automatiquement après votre enregistrement INHP.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.slate500),
            ),
          ],
        ),
      ),
    );
  }
}

/// Fallback : si l'endpoint public ne renvoie rien (utilisateur agent
/// sans `public_id` ou erreur réseau persistante), on tente la version
/// résumée /api/mobile/followups/ pour ne pas afficher d'écran vide.
class _FallbackToSummary extends ConsumerWidget {
  const _FallbackToSummary({this.error});
  final Object? error;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(followupSummaryProvider);
    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            "Impossible de charger votre suivi pour le moment.\n"
            "Réessayez dans un instant.",
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.slate500),
          ),
        ),
      ),
      data: (s) {
        if (!s.active) return const _InactiveState();
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.ciOrange, AppColors.ciGreen],
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Jour ${s.day.clamp(1, s.totalDays)} / ${s.totalDays}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: s.totalDays == 0
                          ? 0
                          : (s.day / s.totalDays).clamp(0.0, 1.0),
                      backgroundColor: Colors.white24,
                      valueColor: const AlwaysStoppedAnimation<Color>(
                          Colors.white),
                      minHeight: 8,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            if (s.checkinTodayDone)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.statusOk.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.check_circle, color: AppColors.statusOk),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Check-in du jour validé',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: AppColors.statusOk,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => context.push(AppRoutes.checkin),
                  icon: const Icon(Icons.health_and_safety),
                  label: const Text('Faire mon check-in du jour'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
