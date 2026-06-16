import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Anneau de progression animé style Apple Health.
/// `progress` entre 0.0 et 1.0 — animé sur 800 ms à chaque changement.
class AnimatedRing extends StatefulWidget {
  const AnimatedRing({
    super.key,
    required this.progress,
    this.size = 140,
    this.strokeWidth = 14,
    this.color = AppColors.ciOrange,
    this.backgroundColor,
    this.label,
    this.valueText,
    this.duration = const Duration(milliseconds: 800),
  });

  final double progress;
  final double size;
  final double strokeWidth;
  final Color color;
  final Color? backgroundColor;
  final String? label;
  final String? valueText;
  final Duration duration;

  @override
  State<AnimatedRing> createState() => _AnimatedRingState();
}

class _AnimatedRingState extends State<AnimatedRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late Animation<double> _anim;
  double _current = 0;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: widget.duration);
    _anim = Tween<double>(begin: 0, end: widget.progress.clamp(0, 1))
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic))
      ..addListener(() => setState(() => _current = _anim.value));
    _ctrl.forward();
  }

  @override
  void didUpdateWidget(covariant AnimatedRing old) {
    super.didUpdateWidget(old);
    if (old.progress != widget.progress) {
      _anim = Tween<double>(begin: _current, end: widget.progress.clamp(0, 1))
          .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic))
        ..addListener(() => setState(() => _current = _anim.value));
      _ctrl
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bg = widget.backgroundColor ??
        widget.color.withValues(alpha: 0.15);
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(widget.size, widget.size),
            painter: _RingPainter(
              progress: _current,
              color: widget.color,
              backgroundColor: bg,
              strokeWidth: widget.strokeWidth,
            ),
          ),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (widget.valueText != null)
                Text(
                  widget.valueText!,
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: widget.size * 0.22,
                    color: widget.color,
                    height: 1.0,
                  ),
                ),
              if (widget.label != null) ...[
                const SizedBox(height: 4),
                Text(
                  widget.label!,
                  style: TextStyle(
                    color: AppColors.slate500,
                    fontSize: widget.size * 0.085,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.color,
    required this.backgroundColor,
    required this.strokeWidth,
  });

  final double progress;
  final Color color;
  final Color backgroundColor;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = (math.min(size.width, size.height) - strokeWidth) / 2;

    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, bgPaint);

    final fgPaint = Paint()
      ..shader = SweepGradient(
        startAngle: -math.pi / 2,
        endAngle: 3 * math.pi / 2,
        colors: [color.withValues(alpha: 0.8), color],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final sweep = 2 * math.pi * progress.clamp(0.0, 1.0);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweep,
      false,
      fgPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.progress != progress ||
      old.color != color ||
      old.strokeWidth != strokeWidth;
}
