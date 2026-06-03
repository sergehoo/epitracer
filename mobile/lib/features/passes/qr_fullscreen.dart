import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/theme/app_colors.dart';

class QrFullscreenScreen extends StatefulWidget {
  const QrFullscreenScreen({super.key, required this.passId});

  final int passId;

  @override
  State<QrFullscreenScreen> createState() => _QrFullscreenScreenState();
}

class _QrFullscreenScreenState extends State<QrFullscreenScreen> {
  @override
  void initState() {
    super.initState();
    // Augmente la luminosité au max pour faciliter le scan
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.light);
  }

  @override
  Widget build(BuildContext context) {
    const qrPayload = 'epitrace://pass/PASS-XYZ12345/demo-signature';
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(
                icon: const Icon(Icons.close, color: Colors.white, size: 30),
                onPressed: () => Navigator.pop(context),
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
              ),
              child: QrImageView(
                data: qrPayload,
                version: QrVersions.auto,
                size: 320,
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
            const SizedBox(height: 24),
            const Text(
              'Présentez ce QR à l\'agent INHP',
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'PASS-XYZ12345',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontFamily: 'monospace',
                letterSpacing: 1.5,
              ),
            ),
            const Spacer(),
          ],
        ),
      ),
    );
  }
}
