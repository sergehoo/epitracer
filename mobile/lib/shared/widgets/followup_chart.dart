import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'glass_card.dart';

/// Courbe d'évolution du suivi 21 jours — un point par jour, déjà fait ou pas.
class FollowupChart extends StatelessWidget {
  const FollowupChart({
    super.key,
    required this.currentDay,
    required this.totalDays,
    required this.completedDays,
  });

  final int currentDay;
  final int totalDays;

  /// Indices de jours (1..totalDays) où le check-in a été fait.
  final List<int> completedDays;

  @override
  Widget build(BuildContext context) {
    final spots = List<FlSpot>.generate(
      totalDays,
      (i) {
        final day = i + 1;
        final done = completedDays.contains(day);
        return FlSpot(day.toDouble(), done ? 1.0 : 0.0);
      },
    );

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.timeline, color: AppColors.ciGreen, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Évolution du suivi',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
              const Spacer(),
              Text(
                'Jour $currentDay / $totalDays',
                style: const TextStyle(
                  color: AppColors.slate500,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 140,
            child: LineChart(
              LineChartData(
                minX: 1,
                maxX: totalDays.toDouble(),
                minY: 0,
                maxY: 1.2,
                gridData: const FlGridData(show: false),
                titlesData: FlTitlesData(
                  leftTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 24,
                      interval: 5,
                      getTitlesWidget: (value, _) => Text(
                        'J${value.toInt()}',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.slate500,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    curveSmoothness: 0.35,
                    color: AppColors.ciGreen,
                    barWidth: 3,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, percent, bar, index) {
                        final done = spot.y > 0;
                        return FlDotCirclePainter(
                          radius: done ? 4 : 2,
                          color: done ? AppColors.ciGreen : AppColors.slate300,
                          strokeColor: Colors.white,
                          strokeWidth: 2,
                        );
                      },
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          AppColors.ciGreen.withValues(alpha: 0.3),
                          AppColors.ciGreen.withValues(alpha: 0.0),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOutCubic,
            ),
          ),
        ],
      ),
    );
  }
}
