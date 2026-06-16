import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/storage/local_cache.dart';

class AppNotification {
  AppNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.read,
    required this.createdAt,
    this.kind,
    this.payload,
  });

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: (j['id'] as num?)?.toInt() ?? 0,
        title: (j['title'] ?? '').toString(),
        body: (j['body'] ?? j['message'] ?? '').toString(),
        read: j['read'] == true,
        createdAt: DateTime.tryParse(j['created_at']?.toString() ?? '') ??
            DateTime.now(),
        kind: j['kind']?.toString(),
        payload: j['payload'] is Map<String, dynamic>
            ? j['payload'] as Map<String, dynamic>
            : null,
      );

  final int id;
  final String title;
  final String body;
  final bool read;
  final DateTime createdAt;
  final String? kind;
  final Map<String, dynamic>? payload;
}

class NotificationsRepository {
  NotificationsRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  Future<List<AppNotification>> fetchAll() async {
    try {
      final r = await _api.dio.get('/notifications/');
      final raw = r.data;
      final list = (raw is List ? raw : raw['results'] ?? []) as List;
      await _cache.putJson(CacheKeys.notifications, list);
      return list
          .whereType<Map<String, dynamic>>()
          .map(AppNotification.fromJson)
          .toList();
    } on DioException {
      final cached = _cache.getJson(CacheKeys.notifications);
      if (cached is List) {
        return cached
            .whereType<Map<String, dynamic>>()
            .map(AppNotification.fromJson)
            .toList();
      }
      return [];
    }
  }

  Future<bool> markRead(int id) async {
    try {
      await _api.dio.post('/notifications/$id/read/');
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> registerDevice({
    required String fcmToken,
    required String platform,
    String? deviceId,
  }) async {
    try {
      await _api.dio.post('/devices/', data: {
        'fcm_token': fcmToken,
        'platform': platform,
        if (deviceId != null) 'device_id': deviceId,
      });
      return true;
    } catch (_) {
      return false;
    }
  }
}

final notificationsRepositoryProvider =
    Provider<NotificationsRepository>((ref) {
  return NotificationsRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final notificationsProvider = FutureProvider<List<AppNotification>>((ref) {
  return ref.watch(notificationsRepositoryProvider).fetchAll();
});

final unreadCountProvider = Provider<int>((ref) {
  final notifs = ref.watch(notificationsProvider).asData?.value ?? [];
  return notifs.where((n) => !n.read).length;
});
