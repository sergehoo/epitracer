import 'package:flutter/material.dart';

/// Compteur numérique qui s'anime de 0 → value sur 1.2 s.
/// Utile pour KPIs du dashboard ("12 pass actifs" qui défile).
class AnimatedCounter extends StatelessWidget {
  const AnimatedCounter({
    super.key,
    required this.value,
    this.duration = const Duration(milliseconds: 1200),
    this.style,
    this.suffix = '',
    this.prefix = '',
    this.curve = Curves.easeOutCubic,
  });

  final num value;
  final Duration duration;
  final TextStyle? style;
  final String suffix;
  final String prefix;
  final Curve curve;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: value.toDouble()),
      duration: duration,
      curve: curve,
      builder: (context, v, _) {
        final display = value is int ? v.round().toString() : v.toStringAsFixed(1);
        return Text(
          '$prefix$display$suffix',
          style: style ?? Theme.of(context).textTheme.displaySmall,
        );
      },
    );
  }
}
