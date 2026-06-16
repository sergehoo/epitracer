import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/models/health_pass.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/glass_card.dart';
import 'passes_repository.dart';

class PassDetailScreen extends ConsumerWidget {
  const PassDetailScreen({super.key, required this.passId});

  final int passId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(passByIdProvider(passId));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Détail du pass'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download_outlined),
            tooltip: 'Télécharger le PDF',
            onPressed: () {
              final p = async.asData?.value;
              if (p?.pdfUrl != null) _openUrl(p!.pdfUrl!);
            },
          ),
          IconButton(
            icon: const Icon(Icons.share_outlined),
            tooltip: 'Partager',
            onPressed: () {
              final p = async.asData?.value;
              if (p != null) _share(p);
            },
          ),
          PopupMenuButton<String>(
            onSelected: (v) {
              final p = async.asData?.value;
              if (p == null) return;
              if (v == 'wallet') _addToWallet(context, p);
              if (v == 'nfc') _shareViaNfc(context, p);
              if (v == 'whatsapp') _shareWhatsApp(p);
            },
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'whatsapp',
                child: Row(children: [
                  Icon(Icons.chat, size: 18),
                  SizedBox(width: 8),
                  Text('Partager via WhatsApp'),
                ]),
              ),
              PopupMenuItem(
                value: 'wallet',
                child: Row(children: [
                  Icon(Icons.account_balance_wallet_outlined, size: 18),
                  SizedBox(width: 8),
                  Text('Ajouter au Wallet'),
                ]),
              ),
              PopupMenuItem(
                value: 'nfc',
                child: Row(children: [
                  Icon(Icons.nfc, size: 18),
                  SizedBox(width: 8),
                  Text('Partager par NFC'),
                ]),
              ),
            ],
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Pass introuvable')),
        data: (p) {
          if (p == null) return const Center(child: Text('Pass introuvable'));
          return _PassContent(pass: p);
        },
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _share(HealthPass p) async {
    final df = DateFormat('dd/MM/yyyy');
    final text =
        'Mon Pass Sanitaire — Côte d\'Ivoire\n\n'
        'Voyageur : ${p.travelerFullName}\n'
        'Pass : ${p.passNumber}\n'
        'Maladie : ${p.diseaseName}\n'
        'Valide du ${df.format(p.issuedAt)} au ${df.format(p.expiresAt)}\n\n'
        'Vérifiez ce pass : ${p.pdfUrl ?? "https://veillesanitaire.com/verifier"}';
    await Share.share(text, subject: 'Mon Pass Sanitaire — ${p.passNumber}');
  }

  Future<void> _shareWhatsApp(HealthPass p) async {
    final df = DateFormat('dd/MM/yyyy');
    final msg = Uri.encodeComponent(
      'Voici mon pass sanitaire INHP CI :\n'
      '${p.passNumber} (${p.diseaseName})\n'
      'Valide jusqu\'au ${df.format(p.expiresAt)}.\n'
      '${p.pdfUrl ?? ""}',
    );
    final uri = Uri.parse('https://wa.me/?text=$msg');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _addToWallet(BuildContext context, HealthPass p) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
            'Ajout Wallet — nécessite la génération .pkpass côté backend (Phase 7H bis)'),
      ),
    );
  }

  void _shareViaNfc(BuildContext context, HealthPass p) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
            'NFC — approchez votre téléphone du lecteur agent (Phase 7H bis)'),
      ),
    );
  }
}

class _PassContent extends StatelessWidget {
  const _PassContent({required this.pass});
  final HealthPass pass;

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy');
    final qrData = pass.qrPayload.isNotEmpty
        ? pass.qrPayload
        : 'epitrace://pass/${pass.passNumber}';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // Hero card avec gradient + badge état
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: pass.isValid
                  ? AppGradients.healthyGreen
                  : AppGradients.warmOrange,
              borderRadius: BorderRadius.circular(24),
              boxShadow: AppShadows.elevated(
                pass.isValid ? AppColors.ciGreen : AppColors.ciOrange,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.22),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        pass.status.label.toUpperCase(),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                        ),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      pass.diseaseName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Text(
                  pass.travelerFullName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  pass.passNumber,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 13,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _HeroDate(
                        label: 'Émis',
                        value: df.format(pass.issuedAt),
                      ),
                    ),
                    Container(
                      width: 1,
                      height: 36,
                      color: Colors.white.withValues(alpha: 0.3),
                    ),
                    Expanded(
                      child: _HeroDate(
                        label: 'Expire',
                        value: df.format(pass.expiresAt),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // QR code dans GlassCard cliquable plein écran
          GlassCard(
            onTap: () => context.push('/passes/${pass.id}/qr'),
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                QrImageView(
                  data: qrData,
                  version: QrVersions.auto,
                  size: 220,
                  eyeStyle: const QrEyeStyle(
                    eyeShape: QrEyeShape.square,
                    color: AppColors.ciDark,
                  ),
                  dataModuleStyle: const QrDataModuleStyle(
                    dataModuleShape: QrDataModuleShape.square,
                    color: AppColors.ciDark,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const [
                    Icon(Icons.touch_app,
                        size: 14, color: AppColors.slate500),
                    SizedBox(width: 6),
                    Text(
                      'Touchez pour afficher en grand',
                      style: TextStyle(
                          color: AppColors.slate500, fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),
          GlassCard(
            child: Column(
              children: [
                _DetailRow(label: 'Statut', value: pass.status.label),
                const Divider(),
                if (pass.entryPointName != null) ...[
                  _DetailRow(
                      label: 'Point d\'entrée',
                      value: pass.entryPointName!),
                  const Divider(),
                ],
                _DetailRow(label: 'Code maladie', value: pass.diseaseCode),
                const Divider(),
                _DetailRow(label: 'ID public', value: pass.publicId, mono: true),
              ],
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
            child: Row(
              children: const [
                Icon(Icons.verified_user,
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
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _HeroDate extends StatelessWidget {
  const _HeroDate({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          label.toUpperCase(),
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.7),
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
    this.mono = false,
  });

  final String label;
  final String value;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style:
                  const TextStyle(color: AppColors.slate500, fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontFamily: mono ? 'monospace' : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
