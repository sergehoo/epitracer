import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';

class PassesListScreen extends StatelessWidget {
  const PassesListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Données de démo — branchera l'API en Phase 2
    final demoPasses = [
      _DemoPass(
        passNumber: 'PASS-XYZ12345',
        disease: 'Ebola',
        status: 'Actif',
        issued: DateTime.now().subtract(const Duration(days: 5)),
        expires: DateTime.now().add(const Duration(days: 16)),
        color: AppColors.statusOk,
      ),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Mes pass sanitaires')),
      body: demoPasses.isEmpty
          ? _EmptyState()
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: demoPasses.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final p = demoPasses[i];
                final df = DateFormat('dd/MM/yyyy');
                return Card(
                  child: InkWell(
                    onTap: () => context.push('/passes/${i + 1}'),
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
                                      p.disease,
                                      style: const TextStyle(fontWeight: FontWeight.w700),
                                    ),
                                    Text(
                                      p.passNumber,
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
                                  color: p.color.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  p.status,
                                  style: TextStyle(
                                    color: p.color,
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
                                  value: df.format(p.issued),
                                ),
                              ),
                              Expanded(
                                child: _InfoTile(
                                  label: 'Expire',
                                  value: df.format(p.expires),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

class _DemoPass {
  _DemoPass({
    required this.passNumber,
    required this.disease,
    required this.status,
    required this.issued,
    required this.expires,
    required this.color,
  });

  final String passNumber;
  final String disease;
  final String status;
  final DateTime issued;
  final DateTime expires;
  final Color color;
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
              onPressed: () {},
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Scanner mon pass'),
            ),
          ],
        ),
      ),
    );
  }
}
