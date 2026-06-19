import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/afriq_credit_footer.dart';
import 'voyageur_auth_repository.dart';

/// Connexion voyageur — minimaliste, sans mot de passe.
/// Entrée : passeport OU téléphone, puis OTP SMS sur le numéro déclaré
/// lors de l'enregistrement sur veillesanitaire.com.
class VoyageurLoginScreen extends ConsumerStatefulWidget {
  const VoyageurLoginScreen({super.key});

  @override
  ConsumerState<VoyageurLoginScreen> createState() =>
      _VoyageurLoginScreenState();
}

class _VoyageurLoginScreenState extends ConsumerState<VoyageurLoginScreen> {
  final _passport = TextEditingController();
  final _phone = TextEditingController();
  final _otp = TextEditingController();

  String _phoneMasked = '';
  bool _step2 = false; // true = saisie OTP
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _passport.dispose();
    _phone.dispose();
    _otp.dispose();
    super.dispose();
  }

  Future<void> _requestOtp() async {
    if (_passport.text.trim().isEmpty && _phone.text.trim().isEmpty) {
      setState(() => _error = 'Saisissez votre passeport ou votre téléphone');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final r = await ref.read(voyageurAuthRepositoryProvider).requestOtp(
          passportNumber: _passport.text.trim(),
          phone: _phone.text.trim(),
        );
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r.ok) {
        _step2 = true;
        _phoneMasked = r.phoneMasked;
      } else {
        _error = r.error ?? 'Impossible de demander un code.';
      }
    });
  }

  Future<void> _verifyOtp() async {
    if (_otp.text.trim().length != 6) {
      setState(() => _error = 'Le code SMS doit contenir 6 chiffres');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final r = await ref.read(voyageurAuthRepositoryProvider).verifyOtp(
          passportNumber: _passport.text.trim(),
          phone: _phone.text.trim(),
          code: _otp.text.trim(),
        );
    if (!mounted) return;
    setState(() => _busy = false);
    if (r.ok) {
      context.go(AppRoutes.dashboard);
    } else {
      setState(() => _error = r.error ?? 'Code invalide');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.neutralLight),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 40, 24, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Bandeau institutionnel
                const OfficialLogosBanner(size: 44),
                const SizedBox(height: 20),
                Center(
                  child: Container(
                    height: 72,
                    width: 72,
                    decoration: BoxDecoration(
                      gradient: AppGradients.healthyGreen,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: AppShadows.elevated(AppColors.ciGreen),
                    ),
                    child: const Icon(
                      Icons.health_and_safety,
                      color: Colors.white,
                      size: 36,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Mon Pass Sanitaire',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: AppColors.ciDark,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'République de Côte d\'Ivoire — INHP',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.slate500,
                    fontSize: 13,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 40),
                if (!_step2) ..._step1Form() else ..._step2Form(),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.statusDanger.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AppColors.statusDanger.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline,
                            color: AppColors.statusDanger, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _error!,
                            style: const TextStyle(
                              color: AppColors.statusDanger,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 32),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.lock_outline,
                        size: 14, color: AppColors.slate500),
                    const SizedBox(width: 6),
                    const Text(
                      'Pas encore de pass ? ',
                      style: TextStyle(color: AppColors.slate500, fontSize: 13),
                    ),
                    TextButton(
                      onPressed: () => context.push(AppRoutes.registration),
                      child: const Text(
                        'M\'enregistrer',
                        style: TextStyle(
                          color: AppColors.ciOrange,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Center(
                  child: TextButton.icon(
                    onPressed: () => context.go(AppRoutes.login),
                    icon: const Icon(Icons.shield_outlined,
                        size: 14, color: AppColors.slate500),
                    label: const Text(
                      'Je suis agent INHP',
                      style: TextStyle(
                        color: AppColors.slate500,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Divider(color: AppColors.slate200, height: 1),
                const AfriqCreditFooter(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _step1Form() => [
        TextField(
          controller: _passport,
          textCapitalization: TextCapitalization.characters,
          decoration: InputDecoration(
            labelText: 'Numéro de passeport',
            prefixIcon: const Icon(Icons.badge_outlined),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
            ),
            filled: true,
            fillColor: Colors.white,
          ),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 16),
          child: Row(
            children: [
              Expanded(child: Divider(color: AppColors.slate200)),
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  'OU',
                  style: TextStyle(
                    color: AppColors.slate500,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                  ),
                ),
              ),
              Expanded(child: Divider(color: AppColors.slate200)),
            ],
          ),
        ),
        TextField(
          controller: _phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d+ ]'))],
          decoration: InputDecoration(
            labelText: 'Téléphone (+225 ...)',
            prefixIcon: const Icon(Icons.phone_outlined),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
            ),
            filled: true,
            fillColor: Colors.white,
          ),
        ),
        const SizedBox(height: 20),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.ciGreen,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: _busy ? null : _requestOtp,
          child: _busy
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white),
                )
              : const Text(
                  'Recevoir un code SMS',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
        ),
      ];

  List<Widget> _step2Form() => [
        Text(
          'Code SMS envoyé',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w800,
                color: AppColors.ciDark,
              ),
        ),
        const SizedBox(height: 6),
        Text(
          'Un code à 6 chiffres a été envoyé au ${_phoneMasked.isEmpty ? "numéro renseigné" : _phoneMasked}.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.slate500, fontSize: 13),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _otp,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            letterSpacing: 12,
          ),
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: InputDecoration(
            counterText: '',
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
            ),
            filled: true,
            fillColor: Colors.white,
          ),
        ),
        const SizedBox(height: 16),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.ciOrange,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: _busy ? null : _verifyOtp,
          child: _busy
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white),
                )
              : const Text(
                  'Valider',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
        ),
        const SizedBox(height: 8),
        TextButton(
          onPressed: _busy
              ? null
              : () {
                  setState(() {
                    _step2 = false;
                    _otp.clear();
                  });
                },
          child: const Text(
            'Modifier le numéro',
            style: TextStyle(color: AppColors.slate500),
          ),
        ),
      ];
}
