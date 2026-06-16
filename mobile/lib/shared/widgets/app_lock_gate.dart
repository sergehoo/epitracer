import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/security/biometric_service.dart';
import '../../core/theme/app_colors.dart';

/// Verrou biométrique global, monté autour de MaterialApp.
/// Si l'utilisateur a activé le verrouillage, l'app est masquée jusqu'à
/// une auth réussie. Si l'auth échoue, on garde l'écran de lock.
class AppLockGate extends ConsumerStatefulWidget {
  const AppLockGate({super.key, required this.child});
  final Widget child;

  @override
  ConsumerState<AppLockGate> createState() => _AppLockGateState();
}

class _AppLockGateState extends ConsumerState<AppLockGate>
    with WidgetsBindingObserver {
  bool _unlocked = true; // par défaut on n'enclenche le lock que si activé
  bool _checked = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkOnBoot();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _enforceLockIfEnabled();
    } else if (state == AppLifecycleState.resumed && !_unlocked) {
      _promptUnlock();
    }
  }

  Future<void> _checkOnBoot() async {
    final enabled = await ref.read(biometricServiceProvider).isEnabled();
    if (!mounted) return;
    setState(() {
      _checked = true;
      _unlocked = !enabled;
    });
    if (enabled) _promptUnlock();
  }

  Future<void> _enforceLockIfEnabled() async {
    final enabled = await ref.read(biometricServiceProvider).isEnabled();
    if (!mounted) return;
    if (enabled) setState(() => _unlocked = false);
  }

  Future<void> _promptUnlock() async {
    final ok = await ref.read(biometricServiceProvider).authenticate();
    if (!mounted) return;
    if (ok) setState(() => _unlocked = true);
  }

  @override
  Widget build(BuildContext context) {
    if (!_checked) {
      return const ColoredBox(
        color: Colors.white,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return Stack(
      children: [
        widget.child,
        if (!_unlocked)
          Positioned.fill(
            child: ColoredBox(
              color: AppColors.ciDark,
              child: SafeArea(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.fingerprint,
                          size: 96, color: Colors.white70),
                      const SizedBox(height: 16),
                      const Text(
                        'Application verrouillée',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 32),
                        child: Text(
                          "Utilisez votre biométrie ou code d'écran pour continuer.",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white70),
                        ),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: _promptUnlock,
                        icon: const Icon(Icons.lock_open),
                        label: const Text('Déverrouiller'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: AppColors.ciDark,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 24, vertical: 12),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
