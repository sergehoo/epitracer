import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/router/app_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _logoCtrl;
  late final AnimationController _textCtrl;
  late final Animation<double> _logoScale;
  late final Animation<double> _logoRotate;
  late final Animation<double> _textOpacity;
  late final Animation<Offset> _textSlide;

  @override
  void initState() {
    super.initState();

    _logoCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _textCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _logoScale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.0, end: 1.15)
            .chain(CurveTween(curve: Curves.easeOutBack)),
        weight: 65,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.15, end: 1.0)
            .chain(CurveTween(curve: Curves.easeOutCubic)),
        weight: 35,
      ),
    ]).animate(_logoCtrl);

    _logoRotate = Tween<double>(begin: -0.3, end: 0.0)
        .chain(CurveTween(curve: Curves.easeOutCubic))
        .animate(_logoCtrl);

    _textOpacity = CurvedAnimation(parent: _textCtrl, curve: Curves.easeOut);
    _textSlide = Tween<Offset>(
      begin: const Offset(0, 0.4),
      end: Offset.zero,
    ).chain(CurveTween(curve: Curves.easeOutCubic)).animate(_textCtrl);

    _logoCtrl.forward().then((_) => _textCtrl.forward());

    Future.microtask(_route);
  }

  Future<void> _route() async {
    await Future<void>.delayed(const Duration(milliseconds: 2400));
    if (!mounted) return;

    final prefs = await SharedPreferences.getInstance();
    final seen = prefs.getBool('onboarding_seen') ?? false;

    if (!seen) {
      context.go(AppRoutes.onboarding);
      return;
    }

    final hasSession = await ref.read(secureStorageProvider).hasSession();
    if (!mounted) return;
    context.go(hasSession ? AppRoutes.dashboard : AppRoutes.voyageurLogin);
  }

  @override
  void dispose() {
    _logoCtrl.dispose();
    _textCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.nightDark),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Logo animé : scale + rotate + glow
              AnimatedBuilder(
                animation: _logoCtrl,
                builder: (_, __) => Transform.scale(
                  scale: _logoScale.value,
                  child: Transform.rotate(
                    angle: _logoRotate.value,
                    child: Container(
                      height: 120,
                      width: 120,
                      decoration: BoxDecoration(
                        gradient: AppGradients.ciFlag,
                        borderRadius: BorderRadius.circular(32),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.ciOrange.withValues(alpha: 0.5),
                            blurRadius: 40,
                            spreadRadius: 8,
                          ),
                          BoxShadow(
                            color: AppColors.ciGreen.withValues(alpha: 0.3),
                            blurRadius: 60,
                            spreadRadius: 4,
                            offset: const Offset(0, 10),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.health_and_safety,
                        color: Colors.white,
                        size: 64,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Texte slide-up + fade
              SlideTransition(
                position: _textSlide,
                child: FadeTransition(
                  opacity: _textOpacity,
                  child: Column(
                    children: [
                      const Text(
                        'Mon Pass Sanitaire',
                        style: TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 0.3,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'INHP · République de Côte d\'Ivoire',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withValues(alpha: 0.65),
                          letterSpacing: 2.0,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 64),

              // Loader trois points animés
              const _DotsLoader(),
            ],
          ),
        ),
      ),
    );
  }
}

/// Trois points qui pulsent en cascade — alternative subtile au spinner.
class _DotsLoader extends StatefulWidget {
  const _DotsLoader();

  @override
  State<_DotsLoader> createState() => _DotsLoaderState();
}

class _DotsLoaderState extends State<_DotsLoader>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 60,
      height: 16,
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (_, __) {
          return Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: List.generate(3, (i) {
              final progress = (_ctrl.value - i * 0.15) % 1.0;
              final scale = 0.5 + (progress < 0.5 ? progress : 1 - progress);
              return Container(
                width: 10,
                height: 10,
                transform: Matrix4.identity()..scale(scale, scale),
                transformAlignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.ciOrange.withValues(alpha: 0.7 + scale * 0.3),
                  shape: BoxShape.circle,
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
