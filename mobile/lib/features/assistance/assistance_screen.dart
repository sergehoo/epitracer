import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';

class AssistanceScreen extends StatelessWidget {
  const AssistanceScreen({super.key});

  Future<void> _call(String number) async {
    final uri = Uri(scheme: 'tel', path: number);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Assistance santé')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.statusInfo.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppColors.statusInfo.withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Icon(Icons.support_agent,
                    color: AppColors.statusInfo, size: 32),
                SizedBox(height: 12),
                Text(
                  'Vous n\'êtes pas seul',
                  style:
                      TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                ),
                SizedBox(height: 4),
                Text(
                  'Un service sanitaire peut vous orienter calmement.',
                  style: TextStyle(color: AppColors.statusInfo),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          _ActionTile(
            icon: Icons.phone,
            label: 'Appeler le 143',
            subtitle: 'Numéro vert national, 24h/24',
            color: AppColors.statusDanger,
            onTap: () => _call('143'),
          ),
          _ActionTile(
            icon: Icons.phone,
            label: 'Appeler le 185',
            subtitle: 'Information santé publique',
            color: AppColors.statusInfo,
            onTap: () => _call('185'),
          ),
          _ActionTile(
            icon: Icons.message,
            label: 'Demander un rappel',
            subtitle: 'Un agent INHP vous contactera',
            color: AppColors.ciOrange,
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Demande envoyée (Phase 2)')),
              );
            },
          ),
          _ActionTile(
            icon: Icons.location_on,
            label: 'Centres de santé proches',
            subtitle: 'Voir la liste sur la carte',
            color: AppColors.ciGreen,
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Carte disponible Phase 2')),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color),
        ),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
