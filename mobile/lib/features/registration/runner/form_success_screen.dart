/// Écran de succès post-soumission (Phase 8B).
/// Affiche le pass délivré + QR + boutons d'action.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/router/app_router.dart';
import '../../../core/storage/secure_storage.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_gradients.dart';
import 'runner_models.dart';

class FormSuccessScreen extends ConsumerStatefulWidget {
  const FormSuccessScreen({super.key, required this.result});
  final SubmissionResult result;

  @override
  ConsumerState<FormSuccessScreen> createState() => _FormSuccessScreenState();
}

class _FormSuccessScreenState extends ConsumerState<FormSuccessScreen> {
  @override
  void initState() {
    super.initState();
    // Sauve le public_id en SecureStorage pour login OTP futur sans saisir.
    final pid = widget.result.travelerPublicId;
    if (pid.isNotEmpty) {
      final storage = ref.read(secureStorageProvider);
      // best-effort, pas bloquant
      // ignore: discarded_futures
      storage.savePublicId(pid);
    }
  }

  Future<void> _downloadPdf() async {
    final url = widget.result.pdfUrl;
    if (url == null || url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PDF indisponible pour le moment.')),
      );
      return;
    }
    final uri = Uri.parse(url);
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Impossible d\'ouvrir le PDF.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.healthyGreen),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const SizedBox(height: 12),
                Container(
                  width: 84,
                  height: 84,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.verified,
                      color: Colors.white, size: 48),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Votre pass santé a été créé !',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  r.message,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 22),
                // QR + identifiants
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    children: [
                      if (r.qrToken.isNotEmpty)
                        QrImageView(
                          data: r.qrToken,
                          size: 220,
                          backgroundColor: Colors.white,
                        )
                      else
                        Container(
                          width: 220,
                          height: 220,
                          alignment: Alignment.center,
                          color: AppColors.slate100,
                          child: const Text('QR indisponible'),
                        ),
                      const SizedBox(height: 16),
                      Text(
                        r.passNumber.isNotEmpty
                            ? 'Pass N° ${r.passNumber}'
                            : 'Pass en cours de génération',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          color: AppColors.ciDark,
                        ),
                      ),
                      if (r.travelerPublicId.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          'ID voyageur : ${r.travelerPublicId}',
                          style: const TextStyle(
                            color: AppColors.slate500,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => context.go(AppRoutes.passes),
                    icon: const Icon(Icons.qr_code_2, size: 18),
                    label: const Text('Voir mes pass'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppColors.ciDark,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _downloadPdf,
                    icon: const Icon(Icons.download_outlined, size: 18),
                    label: const Text('Télécharger le PDF'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: BorderSide(
                          color: Colors.white.withValues(alpha: 0.4)),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: () => context.go(AppRoutes.voyageurLogin),
                  child: Text(
                    'Se connecter à mon espace voyageur',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                    ),
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
