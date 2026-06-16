import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/offline_banner.dart';
import 'followup_repository.dart';

class FollowupScreen extends ConsumerWidget {
  const FollowupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(followupSummaryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Suivi sanitaire')),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const _ErrorState(),
              data: (s) {
                if (!s.active) return const _InactiveState();
                final day = s.day.clamp(0, s.totalDays);
                final total = s.totalDays;
                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(followupSummaryProvider),
                  child: ListView(
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
                              'Jour $day / $total',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 28,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: LinearProgressIndicator(
                                value: total == 0 ? 0 : day / total,
                                backgroundColor: Colors.white24,
                                valueColor: const AlwaysStoppedAnimation<Color>(
                                    Colors.white),
                                minHeight: 8,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Encore ${(total - day).clamp(0, total)} jours de suivi sanitaire',
                              style: const TextStyle(color: Colors.white70),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      if (s.checkinTodayDone)
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.statusOk.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            children: const [
                              Icon(Icons.check_circle,
                                  color: AppColors.statusOk),
                              SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  'Check-in du jour validé ✓',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.statusOk),
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        ElevatedButton.icon(
                          onPressed: () => context.push(AppRoutes.checkin),
                          icon: const Icon(Icons.health_and_safety),
                          label: const Text('Faire mon check-in du jour'),
                          style: ElevatedButton.styleFrom(
                            padding:
                                const EdgeInsets.symmetric(vertical: 16),
                          ),
                        ),
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

class _ErrorState extends StatelessWidget {
  const _ErrorState();
  @override
  Widget build(BuildContext context) => const Center(
        child: Text('Erreur de chargement',
            style: TextStyle(color: AppColors.slate500)),
      );
}
