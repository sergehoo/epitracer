import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';

class FollowupScreen extends StatelessWidget {
  const FollowupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const day = 8;
    const total = 21;
    return Scaffold(
      appBar: AppBar(title: const Text('Suivi sanitaire')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Progression suivi
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.ciOrange, AppColors.ciGreen],
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Jour $day / $total',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: day / total,
                    backgroundColor: Colors.white24,
                    valueColor:
                        const AlwaysStoppedAnimation<Color>(Colors.white),
                    minHeight: 8,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Encore ${total - day} jours de suivi sanitaire',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          ElevatedButton.icon(
            onPressed: () => context.push(AppRoutes.checkin),
            icon: const Icon(Icons.health_and_safety),
            label: const Text('Faire mon check-in du jour'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
          const SizedBox(height: 24),

          Text('Historique récent',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final d in List<int>.generate(5, (i) => day - 1 - i))
            ListTile(
              leading: const CircleAvatar(
                backgroundColor: AppColors.statusOk,
                child: Icon(Icons.check, color: Colors.white, size: 18),
              ),
              title: Text('Jour $d'),
              subtitle: const Text('Aucun symptôme déclaré'),
              trailing: const Icon(Icons.chevron_right),
            ),
        ],
      ),
    );
  }
}
