import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'glass_card.dart';

class RegionCases {
  const RegionCases(this.region, this.cases);
  final String region;
  final int cases;
}

/// Graphique barres horizontal des cas de l'épidémie en cours par région CI.
/// Données mockées en attendant l'endpoint /api/mobile/epidemic-stats/.
class RegionCasesChart extends StatelessWidget {
  const RegionCasesChart({super.key, this.data = const []});

  final List<RegionCases> data;

  static const _mock = [
    RegionCases('Abidjan', 142),
    RegionCases('Bouaké', 38),
    RegionCases('Korhogo', 24),
    RegionCases('San-Pédro', 19),
    RegionCases('Yamoussoukro', 12),
  ];

  @override
  Widget build(BuildContext context) {
    final rows = data.isEmpty ? _mock : data;
    final maxValue =
        rows.fold<int>(0, (m, r) => r.cases > m ? r.cases : m).toDouble();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.bar_chart, color: AppColors.ciOrange, size: 18),
              SizedBox(width: 8),
              Text(
                'Épidémie en cours · Côte d\'Ivoire',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 180,
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.spaceAround,
                maxY: maxValue * 1.2,
                barTouchData: BarTouchData(
                  enabled: true,
                  touchTooltipData: BarTouchTooltipData(
                    getTooltipColor: (_) => AppColors.ciDark,
                    getTooltipItem: (group, _, rod, __) => BarTooltipItem(
                      '${rows[group.x].region}\n${rod.toY.toInt()} cas',
                      const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
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
                      reservedSize: 28,
                      getTitlesWidget: (value, _) {
                        final i = value.toInt();
                        if (i < 0 || i >= rows.length) return const SizedBox();
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            rows[i].region,
                            style: const TextStyle(
                              fontSize: 10,
                              color: AppColors.slate500,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                gridData: const FlGridData(show: false),
                borderData: FlBorderData(show: false),
                barGroups: [
                  for (int i = 0; i < rows.length; i++)
                    BarChartGroupData(
                      x: i,
                      barRods: [
                        BarChartRodData(
                          toY: rows[i].cases.toDouble(),
                          width: 18,
                          borderRadius: BorderRadius.circular(6),
                          gradient: const LinearGradient(
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                            colors: [
                              AppColors.ciDark,
                              AppColors.ciOrange,
                            ],
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppColors.ciOrange,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              const Text(
                'Cas confirmés (7 derniers jours)',
                style: TextStyle(
                  fontSize: 11,
                  color: AppColors.slate500,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
