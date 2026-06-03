import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import 'auth_repository.dart';

class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({super.key, required this.email});

  final String email;

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen> {
  final _ctrl = TextEditingController();
  bool _busy = false;
  String? _error;
  int _cooldown = 60;
  Timer? _timer;
  String _password = '';
  String _maskedEmail = '';

  @override
  void initState() {
    super.initState();
    final state = GoRouterState.of(context);
    _password = state.uri.queryParameters['password'] ?? '';
    _maskedEmail = state.uri.queryParameters['masked'] ?? widget.email;
    _startCooldown();
  }

  void _startCooldown() {
    _timer?.cancel();
    setState(() => _cooldown = 60);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_cooldown <= 0) {
        t.cancel();
      } else {
        setState(() => _cooldown--);
      }
    });
  }

  Future<void> _verify() async {
    if (_ctrl.text.length != 6) {
      setState(() => _error = 'Le code doit comporter 6 chiffres');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final r = await ref.read(authRepositoryProvider).verifyOtp(
          email: widget.email,
          password: _password,
          code: _ctrl.text,
        );
    if (!mounted) return;
    setState(() => _busy = false);
    if (r.success) {
      context.go(AppRoutes.dashboard);
    } else {
      setState(() => _error = r.error);
    }
  }

  Future<void> _resend() async {
    if (_cooldown > 0) return;
    final ok = await ref.read(authRepositoryProvider).resendOtp(widget.email);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? 'Nouveau code envoyé' : 'Échec de l\'envoi')),
    );
    if (ok) _startCooldown();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 24),
              Container(
                height: 76,
                width: 76,
                margin: const EdgeInsets.symmetric(horizontal: 100),
                decoration: BoxDecoration(
                  color: AppColors.ciOrange.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(
                  Icons.shield_outlined,
                  size: 40,
                  color: AppColors.ciOrange,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Vérification',
                style: Theme.of(context).textTheme.headlineMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text.rich(
                TextSpan(
                  children: [
                    const TextSpan(text: 'Un code à 6 chiffres a été envoyé à '),
                    TextSpan(
                      text: _maskedEmail,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const TextSpan(text: '. Saisissez-le ci-dessous.'),
                  ],
                ),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.slate500,
                    ),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _ctrl,
                keyboardType: TextInputType.number,
                maxLength: 6,
                autofocus: true,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 12,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                ],
                decoration: const InputDecoration(
                  counterText: '',
                  hintText: '••••••',
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(
                  _error!,
                  style: const TextStyle(color: AppColors.statusDanger),
                  textAlign: TextAlign.center,
                ),
              ],
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _busy || _ctrl.text.length != 6 ? null : _verify,
                child: _busy
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white))
                    : const Text('Valider'),
              ),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _cooldown > 0 ? null : _resend,
                icon: const Icon(Icons.refresh, size: 16),
                label: Text(_cooldown > 0
                    ? 'Renvoyer dans ${_cooldown}s'
                    : 'Renvoyer le code'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
