import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          _NotifTile(
            icon: Icons.medical_services,
            color: AppColors.ciOrange,
            title: 'Rappel : check-in du jour',
            subtitle: 'Jour 8 / 21 — il vous reste 2h',
            time: '14:30',
            unread: true,
          ),
          _NotifTile(
            icon: Icons.vaccines,
            color: AppColors.ciGreen,
            title: 'Rappel : prochaine dose Covid',
            subtitle: 'Prévue le 15/06/2026',
            time: 'Hier',
            unread: false,
          ),
          _NotifTile(
            icon: Icons.info,
            color: AppColors.statusInfo,
            title: 'Nouvelle consigne sanitaire INHP',
            subtitle: 'Vigilance renforcée Ebola — voir détails',
            time: '20 mai',
            unread: false,
          ),
        ],
      ),
    );
  }
}

class _NotifTile extends StatelessWidget {
  const _NotifTile({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.time,
    required this.unread,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final String time;
  final bool unread;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(
          title,
          style: TextStyle(
              fontWeight: unread ? FontWeight.w700 : FontWeight.w500),
        ),
        subtitle: Text(subtitle),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(time, style: const TextStyle(fontSize: 11)),
            if (unread)
              Container(
                margin: const EdgeInsets.only(top: 4),
                height: 8,
                width: 8,
                decoration: const BoxDecoration(
                  color: AppColors.ciOrange,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
