import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/feature_card.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  String _fullName = '';

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    final user = await ref.read(secureStorageProvider).getUser();
    if (mounted) {
      setState(() => _fullName = user['full_name'] ?? '');
    }
  }

  Future<void> _logout() async {
    await ref.read(secureStorageProvider).clearSession();
    if (mounted) context.go(AppRoutes.login);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            await _loadUser();
            await Future<void>.delayed(const Duration(milliseconds: 400));
          },
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            children: [
              // ── Header ──
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Bonjour 👋',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.slate500,
                              ),
                        ),
                        Text(
                          _fullName.isNotEmpty ? _fullName : 'Voyageur',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.notifications_outlined),
                    onPressed: () => context.push(AppRoutes.notifications),
                  ),
                  IconButton(
                    icon: const Icon(Icons.person_outline),
                    onPressed: () => context.push(AppRoutes.profile),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // ── Carte statut principal ──
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.ciDark, AppColors.ciGreen],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.verified_user, color: Colors.white, size: 28),
                        const SizedBox(width: 12),
                        Text(
                          'Statut sanitaire',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Colors.white70,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'À jour',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Aucune alerte sanitaire active.',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        ElevatedButton.icon(
                          onPressed: () => context.push(AppRoutes.passes),
                          icon: const Icon(Icons.qr_code_2, size: 18),
                          label: const Text('Mon pass'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppColors.ciDark,
                            elevation: 0,
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          onPressed: () => context.push(AppRoutes.qrScanner),
                          icon: const Icon(Icons.qr_code_scanner, size: 18),
                          label: const Text('Scanner'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white,
                            side: const BorderSide(color: Colors.white70),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              Text(
                'Mes services',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),

              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.0,
                children: [
                  FeatureCard(
                    icon: Icons.medical_information_outlined,
                    label: 'Mes pass',
                    color: AppColors.ciOrange,
                    onTap: () => context.push(AppRoutes.passes),
                  ),
                  FeatureCard(
                    icon: Icons.vaccines_outlined,
                    label: 'Carnet vaccinal',
                    color: AppColors.ciGreen,
                    onTap: () => context.push(AppRoutes.vaccinations),
                  ),
                  FeatureCard(
                    icon: Icons.favorite_outline,
                    label: 'Suivi sanitaire',
                    color: AppColors.statusInfo,
                    onTap: () => context.push(AppRoutes.followup),
                  ),
                  FeatureCard(
                    icon: Icons.support_agent,
                    label: 'Assistance',
                    color: AppColors.inhpBlue,
                    onTap: () => context.push(AppRoutes.assistance),
                  ),
                ],
              ),

              const SizedBox(height: 24),
              TextButton.icon(
                onPressed: _logout,
                icon: const Icon(Icons.logout, size: 16),
                label: const Text('Se déconnecter'),
                style: TextButton.styleFrom(foregroundColor: AppColors.slate500),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
