import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/push/push_service.dart';
import '../../core/router/app_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/animated_ring.dart';
import '../../shared/widgets/followup_chart.dart';
import '../../shared/widgets/glass_card.dart';
import '../../shared/widgets/offline_banner.dart';
import '../../shared/widgets/stat_card.dart';
import '../education/stories_data.dart';
import '../education/story_viewer.dart';
import '../followup/followup_repository.dart';
import '../notifications/notifications_repository.dart';
import '../passes/passes_repository.dart';
import '../profile/profile_repository.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  Future<void> _logout() async {
    try {
      await ref.read(pushServiceProvider).dispose();
    } catch (_) {/* push pas initialisé */}
    await ref.read(secureStorageProvider).clearSession();
    if (mounted) context.go(AppRoutes.login);
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(profileProvider).asData?.value;
    final fullName = profile?.fullName ?? '';
    final unread = ref.watch(unreadCountProvider);
    final followupAsync = ref.watch(followupSummaryProvider);
    final passesAsync = ref.watch(passesProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final passes = passesAsync.asData?.value ?? const [];
    final followup = followupAsync.asData?.value;
    final activePasses = passes.where((p) => p.isValid).length;
    final expiringSoon = passes.where((p) => p.isExpiringSoon).length;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: isDark
              ? AppGradients.nightDark
              : const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFFFFF7ED), Color(0xFFE0F2F1)],
                ),
        ),
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(profileProvider);
              ref.invalidate(passesProvider);
              ref.invalidate(followupSummaryProvider);
              ref.invalidate(notificationsProvider);
              await Future<void>.delayed(const Duration(milliseconds: 400));
            },
            child: Column(
              children: [
                const OfflineBanner(),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 100),
                    children: [
                      _Header(
                        fullName: fullName,
                        unread: unread,
                        onProfile: () => context.push(AppRoutes.profile),
                        onNotifs: () => context.push(AppRoutes.notifications),
                      ),
                      const SizedBox(height: 20),
                      _HeroStatusCard(
                        passCount: activePasses,
                        followupActive: followup?.active ?? false,
                        followupDay: followup?.day ?? 0,
                        followupTotal: followup?.totalDays ?? 21,
                        checkinDone: followup?.checkinTodayDone ?? false,
                        onTapPass: () => context.push(AppRoutes.passes),
                        onTapScan: () => context.push(AppRoutes.qrScanner),
                      ),
                      const SizedBox(height: 16),
                      _StatsGrid(
                        activePasses: activePasses,
                        expiringSoon: expiringSoon,
                        followupDay: followup?.day ?? 0,
                        unread: unread,
                      ),
                      if (followup?.active ?? false) ...[
                        const SizedBox(height: 16),
                        FollowupChart(
                          currentDay: followup!.day,
                          totalDays: followup.totalDays,
                          completedDays: List<int>.generate(
                            followup.day,
                            (i) => i + 1,
                          ),
                        ),
                      ],
                      const SizedBox(height: 20),
                      _SectionTitle('Apprendre la santé'),
                      const SizedBox(height: 12),
                      const _StoriesStrip(),
                      const SizedBox(height: 20),
                      _SectionTitle('Mes services'),
                      const SizedBox(height: 12),
                      _ServicesGrid(),
                      const SizedBox(height: 20),
                      _SectionTitle('Conseils santé du jour'),
                      const SizedBox(height: 12),
                      const _TipsCarousel(),
                      const SizedBox(height: 24),
                      Center(
                        child: TextButton.icon(
                          onPressed: _logout,
                          icon: const Icon(Icons.logout, size: 16),
                          label: const Text('Se déconnecter'),
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.slate500,
                          ),
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

class _Header extends StatelessWidget {
  const _Header({
    required this.fullName,
    required this.unread,
    required this.onProfile,
    required this.onNotifs,
  });

  final String fullName;
  final int unread;
  final VoidCallback onProfile;
  final VoidCallback onNotifs;

  String _initials() {
    if (fullName.isEmpty) return 'V';
    final parts = fullName.trim().split(RegExp(r'\s+'));
    String first(String s) => s.isEmpty ? '' : s.substring(0, 1);
    if (parts.length == 1) return first(parts.first).toUpperCase();
    return (first(parts.first) + first(parts.last)).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final greet = hour < 12
        ? 'Bonjour'
        : hour < 18
            ? 'Bon après-midi'
            : 'Bonsoir';

    return Row(
      children: [
        InkWell(
          onTap: onProfile,
          borderRadius: BorderRadius.circular(28),
          child: Container(
            height: 48,
            width: 48,
            decoration: BoxDecoration(
              gradient: AppGradients.ciFlag,
              shape: BoxShape.circle,
              boxShadow: AppShadows.soft(AppColors.ciOrange),
            ),
            alignment: Alignment.center,
            child: Text(
              _initials(),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 16,
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                greet,
                style: const TextStyle(
                  color: AppColors.slate500,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                fullName.isNotEmpty ? fullName : 'Voyageur',
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 18,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        _IconBadgeBtn(
          icon: Icons.notifications_outlined,
          badge: unread,
          onTap: onNotifs,
        ),
      ],
    );
  }
}

class _IconBadgeBtn extends StatelessWidget {
  const _IconBadgeBtn({
    required this.icon,
    required this.onTap,
    this.badge = 0,
  });

  final IconData icon;
  final int badge;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.slate200),
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Icon(icon, size: 22, color: AppColors.slate700),
              if (badge > 0)
                Positioned(
                  right: -4,
                  top: -4,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    decoration: const BoxDecoration(
                      color: AppColors.ciOrange,
                      shape: BoxShape.circle,
                    ),
                    constraints:
                        const BoxConstraints(minWidth: 16, minHeight: 16),
                    child: Text(
                      badge > 9 ? '9+' : '$badge',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                      ),
                      textAlign: TextAlign.center,
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

class _HeroStatusCard extends StatelessWidget {
  const _HeroStatusCard({
    required this.passCount,
    required this.followupActive,
    required this.followupDay,
    required this.followupTotal,
    required this.checkinDone,
    required this.onTapPass,
    required this.onTapScan,
  });

  final int passCount;
  final bool followupActive;
  final int followupDay;
  final int followupTotal;
  final bool checkinDone;
  final VoidCallback onTapPass;
  final VoidCallback onTapScan;

  @override
  Widget build(BuildContext context) {
    final progress = followupActive && followupTotal > 0
        ? followupDay / followupTotal
        : (passCount > 0 ? 1.0 : 0.0);
    final ringColor = followupActive
        ? AppColors.ciOrange
        : (passCount > 0 ? AppColors.ciGreen : AppColors.slate300);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppGradients.healthyGreen,
        borderRadius: BorderRadius.circular(28),
        boxShadow: AppShadows.elevated(AppColors.ciGreen, opacity: 0.35),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_user, color: Colors.white, size: 22),
              const SizedBox(width: 8),
              Text(
                'Statut sanitaire',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85),
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              AnimatedRing(
                progress: progress,
                size: 110,
                strokeWidth: 12,
                color: Colors.white,
                backgroundColor: Colors.white.withValues(alpha: 0.18),
                valueText: followupActive ? '$followupDay' : '$passCount',
                label: followupActive ? '/ $followupTotal j' : 'pass',
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      followupActive
                          ? (checkinDone ? 'Tout va bien ✓' : 'Check-in attendu')
                          : (passCount > 0 ? 'Vous êtes en règle' : 'Aucun pass'),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        height: 1.1,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      followupActive
                          ? 'Suivi sanitaire en cours'
                          : (passCount > 0
                              ? 'Votre pass est actif et valide'
                              : 'Importez votre pass via le scanner'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: onTapPass,
                  icon: const Icon(Icons.qr_code_2, size: 18),
                  label: const Text('Mon pass'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.ciDark,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onTapScan,
                  icon: const Icon(Icons.qr_code_scanner, size: 18),
                  label: const Text('Scanner'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: BorderSide(color: Colors.white.withValues(alpha: 0.5)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({
    required this.activePasses,
    required this.expiringSoon,
    required this.followupDay,
    required this.unread,
  });

  final int activePasses;
  final int expiringSoon;
  final int followupDay;
  final int unread;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: StatCard(
            icon: Icons.medical_information_outlined,
            value: activePasses,
            label: 'Pass actifs',
            color: AppColors.ciOrange,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatCard(
            icon: Icons.access_time,
            value: expiringSoon,
            label: 'Bientôt expirés',
            color: AppColors.ciDark,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatCard(
            icon: Icons.timeline,
            value: followupDay,
            label: 'Jours suivi',
            color: AppColors.ciGreen,
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 16,
          ),
        ),
      ],
    );
  }
}

class _ServicesGrid extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // Palette unifiée : orange pour actions primaires, vert pour santé
    // active, dark pour utilitaires. Plus de bleu/teal/rouge ailleurs
    // qu'aux statuts critiques.
    const orange = AppColors.ciOrange;
    const green = AppColors.ciGreen;
    const dark = AppColors.ciDark;
    final tiles = [
      _ServiceTile(
        icon: Icons.medical_information_outlined,
        label: 'Mes pass',
        color: orange,
        route: AppRoutes.passes,
      ),
      _ServiceTile(
        icon: Icons.vaccines_outlined,
        label: 'Vaccinations',
        color: green,
        route: AppRoutes.vaccinations,
      ),
      _ServiceTile(
        icon: Icons.favorite_outline,
        label: 'Suivi 21j',
        color: green,
        route: AppRoutes.followup,
      ),
      _ServiceTile(
        icon: Icons.medical_services_outlined,
        label: 'Carnet santé',
        color: dark,
        route: AppRoutes.medicalRecord,
      ),
      _ServiceTile(
        icon: Icons.map_outlined,
        label: 'Centres santé',
        color: dark,
        route: AppRoutes.map,
      ),
      _ServiceTile(
        icon: Icons.support_agent,
        label: 'Assistance',
        color: orange,
        route: AppRoutes.assistance,
      ),
      _ServiceTile(
        icon: Icons.family_restroom,
        label: 'Ma famille',
        color: orange,
        route: AppRoutes.family,
      ),
      _ServiceTile(
        icon: Icons.school_outlined,
        label: 'Apprendre',
        color: green,
        route: AppRoutes.stories,
      ),
      _ServiceTile(
        icon: Icons.video_call_outlined,
        label: 'Téléconsultation',
        color: dark,
        snackbar: 'Téléconsultation — bientôt disponible',
      ),
    ];
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: tiles.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 0.95,
      ),
      itemBuilder: (_, i) => tiles[i],
    );
  }
}

class _ServiceTile extends StatelessWidget {
  const _ServiceTile({
    required this.icon,
    required this.label,
    required this.color,
    this.route,
    this.snackbar,
  });

  final IconData icon;
  final String label;
  final Color color;
  final String? route;
  final String? snackbar;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      onTap: () {
        if (route != null) {
          context.push(route!);
        } else if (snackbar != null) {
          ScaffoldMessenger.of(context)
              .showSnackBar(SnackBar(content: Text(snackbar!)));
        }
      },
      padding: const EdgeInsets.all(12),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              height: 1.1,
            ),
          ),
        ],
      ),
    );
  }
}

/// Strip horizontal de stories santé style Instagram avec halo coloré.
class _StoriesStrip extends StatelessWidget {
  const _StoriesStrip();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 96,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: kHealthStories.length,
        separatorBuilder: (_, __) => const SizedBox(width: 14),
        itemBuilder: (_, i) {
          final s = kHealthStories[i];
          return InkWell(
            borderRadius: BorderRadius.circular(40),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => StoryViewer(story: s),
                  fullscreenDialog: true,
                ),
              );
            },
            child: SizedBox(
              width: 78,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    height: 64,
                    width: 64,
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      gradient: s.gradient,
                      shape: BoxShape.circle,
                    ),
                    child: Container(
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                      ),
                      padding: const EdgeInsets.all(2),
                      child: Container(
                        decoration: BoxDecoration(
                          color: s.color.withValues(alpha: 0.12),
                          shape: BoxShape.circle,
                        ),
                        alignment: Alignment.center,
                        child: Icon(s.icon, color: s.color, size: 24),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    s.title,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _TipsCarousel extends StatelessWidget {
  const _TipsCarousel();

  @override
  Widget build(BuildContext context) {
    final tips = [
      (
        'Lavez-vous les mains régulièrement',
        'Au savon pendant 20 secondes minimum',
        Icons.wash_outlined,
        AppGradients.healthyGreen,
      ),
      (
        'Hydratez-vous',
        '1,5L d\'eau par jour minimum sous le climat ivoirien',
        Icons.water_drop_outlined,
        AppGradients.nightDark,
      ),
      (
        'Vigilance moustiques',
        'Utilisez moustiquaire + répulsif au crépuscule',
        Icons.bug_report_outlined,
        AppGradients.warmOrange,
      ),
    ];
    return SizedBox(
      height: 150,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: tips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (_, i) {
          final (title, body, icon, gradient) = tips[i];
          return Container(
            width: 280,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppShadows.soft(Colors.black, opacity: 0.12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: Colors.white, size: 20),
                ),
                const SizedBox(height: 12),
                Flexible(
                  child: Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                      height: 1.2,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(height: 4),
                Flexible(
                  child: Text(
                    body,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.88),
                      fontSize: 11.5,
                      height: 1.3,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
