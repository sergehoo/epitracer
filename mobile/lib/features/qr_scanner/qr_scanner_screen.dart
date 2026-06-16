import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/security/qr_verifier.dart';
import '../../core/theme/app_colors.dart';
import '../passes/passes_repository.dart';

class QrScannerScreen extends ConsumerStatefulWidget {
  const QrScannerScreen({super.key});

  @override
  ConsumerState<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends ConsumerState<QrScannerScreen> {
  final _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    facing: CameraFacing.back,
  );
  bool _torch = false;
  bool _handled = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_handled) return;
    final raw = capture.barcodes.firstOrNull?.rawValue;
    if (raw == null || raw.isEmpty) return;
    _handled = true;
    await _controller.stop();

    final result = await ref.read(qrVerifierProvider).verify(raw);
    if (!mounted) return;
    _showResult(raw, result);
  }

  Future<void> _importPass(String raw) async {
    Navigator.pop(context); // ferme le sheet
    final pass =
        await ref.read(passesRepositoryProvider).importQr(raw);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(pass != null
          ? 'Pass ${pass.passNumber} importé ✓'
          : 'Import échoué — réessayez plus tard'),
    ));
    if (pass != null) context.pop();
  }

  void _showResult(String raw, QrVerifyResult result) {
    final ok = result.valid;
    final expired = result.expired;
    final color = ok
        ? AppColors.statusOk
        : (expired ? AppColors.statusWarn : AppColors.statusError);
    final icon = ok
        ? Icons.verified
        : (expired ? Icons.timelapse : Icons.gpp_bad);
    final title = ok
        ? 'Signature valide'
        : (expired ? 'Pass expiré' : 'Signature invalide');

    final payload = result.payload;
    final df = DateFormat('dd/MM/yyyy');

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          left: 24,
          right: 24,
          top: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 32,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 64,
              width: 64,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 40),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(color: color, fontWeight: FontWeight.w800),
              textAlign: TextAlign.center,
            ),
            if (result.reason != null) ...[
              const SizedBox(height: 4),
              Text(
                result.reason!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.slate500),
              ),
            ],
            const SizedBox(height: 16),
            if (payload != null)
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.slate100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _PayloadRow('Pass', payload['pass_number']?.toString()),
                    _PayloadRow('Voyageur', payload['full_name']?.toString()),
                    _PayloadRow('Maladie', payload['disease']?.toString()),
                    _PayloadRow(
                      'Expire',
                      payload['exp'] != null
                          ? df.format(
                              DateTime.tryParse(payload['exp'].toString()) ??
                                  DateTime.now())
                          : null,
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 20),
            if (ok)
              ElevatedButton.icon(
                onPressed: () => _importPass(raw),
                icon: const Icon(Icons.download),
                label: const Text('Importer ce pass'),
              ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () {
                Navigator.pop(context);
                _handled = false;
                _controller.start();
              },
              child: const Text('Scanner à nouveau'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text('Scanner un QR code'),
        actions: [
          IconButton(
            icon: Icon(_torch ? Icons.flash_on : Icons.flash_off),
            onPressed: () {
              _controller.toggleTorch();
              setState(() => _torch = !_torch);
            },
          ),
        ],
      ),
      extendBodyBehindAppBar: true,
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          Center(
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.ciOrange, width: 3),
                borderRadius: BorderRadius.circular(20),
              ),
            ),
          ),
          Positioned(
            bottom: 80,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text(
                  'Vérification Ed25519 hors-ligne',
                  style: TextStyle(color: Colors.white, fontSize: 13),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PayloadRow extends StatelessWidget {
  const _PayloadRow(this.label, this.value);
  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    if (value == null || value!.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(label,
                style: const TextStyle(
                    color: AppColors.slate500, fontSize: 12)),
          ),
          Expanded(
            child: Text(value!,
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
