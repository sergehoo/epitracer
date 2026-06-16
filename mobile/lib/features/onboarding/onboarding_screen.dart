import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _index = 0;

  final _slides = const [
    _Slide(
      icon: Icons.medical_information_outlined,
      title: 'Bienvenue dans\nMon Pass Sanitaire',
      desc: "L'application officielle qui regroupe tous vos documents sanitaires en un seul endroit.",
    ),
    _Slide(
      icon: Icons.qr_code_2_outlined,
      title: 'Vos documents toujours\navec vous',
      desc: 'Pass sanitaire, carnet de vaccination, certificats — accessibles même hors connexion.',
    ),
    _Slide(
      icon: Icons.notifications_active_outlined,
      title: 'Restez informé',
      desc: 'Rappels de suivi, échéances de vaccination, consignes officielles — directement sur votre téléphone.',
    ),
    _Slide(
      icon: Icons.shield_outlined,
      title: 'Vos données protégées',
      desc: "Vous choisissez ce que vous partagez. Aucune information ne quitte l'INHP sans votre accord.",
    ),
  ];

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_seen', true);
    if (!mounted) return;
    context.go(AppRoutes.voyageurLogin);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _index == _slides.length - 1;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.all(8.0),
                child: TextButton(
                  onPressed: _finish,
                  child: const Text('Passer'),
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                onPageChanged: (i) => setState(() => _index = i),
                itemCount: _slides.length,
                itemBuilder: (context, i) => _slides[i],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _slides.length,
                (i) => AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  width: i == _index ? 28 : 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: i == _index ? AppColors.ciOrange : AppColors.slate300,
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    if (isLast) {
                      _finish();
                    } else {
                      _controller.nextPage(
                        duration: const Duration(milliseconds: 280),
                        curve: Curves.easeOut,
                      );
                    }
                  },
                  child: Text(isLast ? 'Commencer' : 'Suivant'),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: () => context.push(AppRoutes.qrScanner),
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Scanner mon QR code'),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _Slide extends StatelessWidget {
  const _Slide({required this.icon, required this.title, required this.desc});

  final IconData icon;
  final String title;
  final String desc;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            height: 140,
            width: 140,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.ciOrange, AppColors.ciGreen],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(32),
            ),
            child: Icon(icon, size: 64, color: Colors.white),
          ),
          const SizedBox(height: 40),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 16),
          Text(
            desc,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.slate500,
                ),
          ),
        ],
      ),
    );
  }
}
