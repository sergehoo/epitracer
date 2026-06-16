import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';
import '../../shared/widgets/offline_banner.dart';
import 'notifications_repository.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const Center(
                  child: Text('Erreur de chargement',
                      style: TextStyle(color: AppColors.slate500))),
              data: (list) {
                if (list.isEmpty) return const _EmptyState();
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(notificationsProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 4),
                    itemBuilder: (_, i) => _NotifTile(
                      notif: list[i],
                      onTap: () async {
                        if (!list[i].read) {
                          await ref
                              .read(notificationsRepositoryProvider)
                              .markRead(list[i].id);
                          ref.invalidate(notificationsProvider);
                        }
                      },
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _NotifTile extends StatelessWidget {
  const _NotifTile({required this.notif, required this.onTap});

  final AppNotification notif;
  final VoidCallback onTap;

  ({IconData icon, Color color}) _iconForKind() {
    switch (notif.kind) {
      case 'vaccine':
        return (icon: Icons.vaccines, color: AppColors.ciGreen);
      case 'alert':
        return (icon: Icons.warning_amber_rounded, color: AppColors.statusError);
      case 'checkin':
        return (icon: Icons.health_and_safety, color: AppColors.ciOrange);
      default:
        return (icon: Icons.notifications, color: AppColors.statusInfo);
    }
  }

  String _formatTime(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 1) return "à l'instant";
    if (diff.inHours < 1) return '${diff.inMinutes} min';
    if (diff.inHours < 24) return DateFormat('HH:mm').format(d);
    if (diff.inDays < 2) return 'Hier';
    return DateFormat('dd MMM', 'fr').format(d);
  }

  @override
  Widget build(BuildContext context) {
    final v = _iconForKind();
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        onTap: onTap,
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: v.color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(v.icon, color: v.color, size: 22),
        ),
        title: Text(
          notif.title.isNotEmpty ? notif.title : 'Notification',
          style: TextStyle(
              fontWeight: notif.read ? FontWeight.w500 : FontWeight.w700),
        ),
        subtitle: Text(notif.body, maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(_formatTime(notif.createdAt),
                style: const TextStyle(fontSize: 11)),
            if (!notif.read)
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

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Icon(Icons.notifications_none,
                  size: 72, color: AppColors.slate300),
              SizedBox(height: 12),
              Text('Aucune notification',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              SizedBox(height: 6),
              Text('Vous recevrez ici vos rappels INHP.',
                  style: TextStyle(color: AppColors.slate500)),
            ],
          ),
        ),
      );
}
