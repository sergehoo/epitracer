import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Bandeau crédit AfriqConsulting affiché en bas des écrans clés.
///
/// Variant `light` (défaut) pour fond clair, variant `dark` pour fond sombre
/// (splash, hero cards). Logo automatiquement adapté.
class AfriqCreditFooter extends StatelessWidget {
  const AfriqCreditFooter({
    super.key,
    this.variant = AfriqVariant.light,
    this.padding = const EdgeInsets.symmetric(vertical: 12),
  });

  final AfriqVariant variant;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final isDark = variant == AfriqVariant.dark;
    final year = DateTime.now().year;
    return Padding(
      padding: padding,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '© $year — Réalisé par ',
            style: TextStyle(
              fontSize: 11,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.6)
                  : AppColors.slate500,
            ),
          ),
          ColorFiltered(
            colorFilter: isDark
                ? const ColorFilter.matrix([
                    -1, 0, 0, 0, 255,
                    0, -1, 0, 0, 255,
                    0, 0, -1, 0, 255,
                    0, 0, 0, 1, 0,
                  ])
                : const ColorFilter.mode(
                    Colors.transparent, BlendMode.dst),
            child: Image.asset(
              'assets/images/afriqconsulting.png',
              height: 16,
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'AfriqConsulting',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: isDark ? Colors.white : AppColors.slate700,
            ),
          ),
        ],
      ),
    );
  }
}

enum AfriqVariant { light, dark }

/// Bandeau officiel MSHPCMU / INHP / Armoiries — pour écrans formels.
class OfficialLogosBanner extends StatelessWidget {
  const OfficialLogosBanner({super.key, this.size = 36});

  /// Hauteur des logos en pixels (défaut 36).
  final double size;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _logo('assets/images/logo-min-sante.png'),
        const SizedBox(width: 16),
        _logo('assets/images/armoirie-ci.png'),
        const SizedBox(width: 16),
        _logo('assets/images/logo-inhp.png'),
      ],
    );
  }

  Widget _logo(String path) {
    return Container(
      height: size,
      width: size,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: const [
          BoxShadow(
            color: Color(0x10000000),
            blurRadius: 6,
            offset: Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.all(3),
      child: Image.asset(path, fit: BoxFit.contain),
    );
  }
}
