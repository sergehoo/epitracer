import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/models/health_pass.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/offline_banner.dart';
import 'passes_repository.dart';

class PassesListScreen extends ConsumerWidget {
  const PassesListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final passesAsync = ref.watch(passesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mes pass sanitaires')),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: passesAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const _ErrorState(),
              data: (passes) {
                if (passes.isEmpty) return const _EmptyState();
                return RefreshIndicator(
                  onRefresh: () async {
                    ref.invalidate(passesProvider);
                  },
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: passes.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, i) =>
                        _PassCard(pass: passes[i]),
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

class _PassCard extends StatelessWidget {
  const _PassCard({required this.pass});
  final HealthPass pass;

  Color _statusColor() {
    switch (pass.status) {
      case PassStatus.active:
        return AppColors.statusOk;
      case PassStatus.expired:
      case PassStatus.revoked:
        return AppColors.statusError;
      case PassStatus.pending:
        return AppColors.statusWarn;
    }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy');
    final color = _statusColor();
    return Card(
      child: InkWell(
        onTap: () => context.push('/passes/${pass.id}'),
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.ciOrange.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.medical_information,
                        color: AppColors.ciOrange),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          pass.disease.isNotEmpty ? pass.disease : 'Pass',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        Text(
                          pass.passNumber,
                          style: const TextStyle(
                              fontSize: 12, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      pass.status.label,
                      style: TextStyle(
                        color: color,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _InfoTile(
                      label: 'Émis',
                      value: df.format(pass.issuedAt),
                    ),
                  ),
                  Expanded(
                    child: _InfoTile(
                      label: 'Expire',
                      value: df.format(pass.expiresAt),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 11, color: AppColors.slate500)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.qr_code_2,
                size: 80, color: AppColors.slate300),
            const SizedBox(height: 16),
            const Text(
              'Aucun pass enregistré',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Text(
              "Scannez votre QR code ou importez-le depuis votre fiche d'enregistrement INHP.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.slate500),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.push(AppRoutes.qrScanner),
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Scanner mon pass'),
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
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.cloud_off, size: 64, color: AppColors.slate300),
            SizedBox(height: 12),
            Text(
              'Impossible de charger vos pass',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 6),
            Text(
              'Vérifiez votre connexion et réessayez.',
              style: TextStyle(color: AppColors.slate500),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
