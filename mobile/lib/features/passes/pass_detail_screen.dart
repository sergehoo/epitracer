import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/theme/app_colors.dart';

class PassDetailScreen extends StatelessWidget {
  const PassDetailScreen({super.key, required this.passId});

  final int passId;

  @override
  Widget build(BuildContext context) {
    // Démo — sera remplacé par appel API en Phase 2
    const passNumber = 'PASS-XYZ12345';
    const fullName = 'Jean DUPONT';
    const disease = 'Ebola';
    const issued = '20/05/2026';
    const expires = '14/06/2026';
    const qrPayload = 'epitrace://pass/$passNumber/demo-signature';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Détail du pass'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download_outlined),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Téléchargement PDF (Phase 2)')),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Partage sécurisé (Phase 2)')),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // QR Code
            GestureDetector(
              onTap: () => context.push('/passes/$passId/qr'),
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.slate200),
                ),
                child: QrImageView(
                  data: qrPayload,
                  version: QrVersions.auto,
                  size: 240,
                  eyeStyle: const QrEyeStyle(
                    eyeShape: QrEyeShape.square,
                    color: AppColors.ciDark,
                  ),
                  dataModuleStyle: const QrDataModuleStyle(
                    dataModuleShape: QrDataModuleShape.square,
                    color: AppColors.ciDark,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Touchez le QR pour l\'afficher en grand',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.slate500,
                  ),
            ),
            const SizedBox(height: 24),

            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: const [
                    _DetailRow(label: 'N° de pass', value: passNumber, mono: true),
                    Divider(),
                    _DetailRow(label: 'Voyageur', value: fullName),
                    Divider(),
                    _DetailRow(label: 'Maladie', value: disease),
                    Divider(),
                    _DetailRow(label: 'Émis le', value: issued),
                    Divider(),
                    _DetailRow(label: 'Valide jusqu\'au', value: expires, highlight: true),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.statusInfo.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.statusInfo.withValues(alpha: 0.3),
                ),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline,
                      color: AppColors.statusInfo, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Ce pass est vérifiable hors-ligne grâce à sa signature cryptographique Ed25519.',
                      style: TextStyle(
                        color: AppColors.statusInfo,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
    this.mono = false,
    this.highlight = false,
  });

  final String label;
  final String value;
  final bool mono;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(label,
                style: const TextStyle(
                    color: AppColors.slate500, fontSize: 13)),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontFamily: mono ? 'monospace' : null,
                color: highlight ? AppColors.ciOrange : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
