import 'package:flutter/material.dart';

import '../../core/config/app_env.dart';
import '../../core/theme/app_colors.dart';

/// Bandeau persistant affiché en haut de l'app uniquement si on tourne
/// sur l'environnement de staging. Évite de confondre une démo staging
/// avec la prod réelle (les pass émis en staging ne sont pas valides en prod).
///
/// Hauteur ~24 px, fond orange "warning", texte court et lisible.
/// S'insère via le `builder:` de MaterialApp.router pour englober TOUTES
/// les routes y compris le splash et les écrans modaux.
class StagingBannerWrapper extends StatelessWidget {
  const StagingBannerWrapper({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!AppEnv.isStaging) return child;
    return Column(
      mainAxisSize: MainAxisSize.max,
      children: [
        Material(
          color: AppColors.ciOrange,
          child: SafeArea(
            bottom: false,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                vertical: 4,
                horizontal: 12,
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.science_outlined,
                      color: Colors.white, size: 14),
                  SizedBox(width: 6),
                  Text(
                    'STAGING — Données de test, pass non valides',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(child: child),
      ],
    );
  }
}
