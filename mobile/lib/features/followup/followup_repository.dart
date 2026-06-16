import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/storage/local_cache.dart';

class FollowupSummary {
  FollowupSummary({
    required this.active,
    required this.day,
    required this.totalDays,
    required this.checkinTodayDone,
    this.startedAt,
    this.endsAt,
  });

  factory FollowupSummary.fromJson(Map<String, dynamic> j) => FollowupSummary(
        active: j['active'] == true,
        day: (j['day'] as num?)?.toInt() ?? 0,
        totalDays: (j['total_days'] as num?)?.toInt() ?? 21,
        checkinTodayDone: j['checkin_today_done'] == true,
        startedAt: j['started_at'] != null
            ? DateTime.tryParse(j['started_at'].toString())
            : null,
        endsAt: j['ends_at'] != null
            ? DateTime.tryParse(j['ends_at'].toString())
            : null,
      );

  final bool active;
  final int day;
  final int totalDays;
  final bool checkinTodayDone;
  final DateTime? startedAt;
  final DateTime? endsAt;
}

class FollowupRepository {
  FollowupRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  Future<FollowupSummary> fetchSummary() async {
    try {
      final r = await _api.dio.get('/followups/');
      final data = r.data as Map<String, dynamic>;
      await _cache.putJson(CacheKeys.followup, data);
      return FollowupSummary.fromJson(data);
    } on DioException {
      final cached = _cache.getJson(CacheKeys.followup);
      if (cached is Map<String, dynamic>) {
        return FollowupSummary.fromJson(cached);
      }
      return FollowupSummary(
        active: false, day: 0, totalDays: 21, checkinTodayDone: false,
      );
    }
  }

  /// Soumet un check-in quotidien. Si offline, draft sauvegardé pour sync.
  Future<bool> submitCheckin(Map<String, dynamic> payload) async {
    try {
      await _api.dio.post('/checkins/', data: payload);
      return true;
    } on DioException {
      final draftId = 'checkin_${DateTime.now().millisecondsSinceEpoch}';
      await _cache.saveDraft(draftId, payload);
      return false;
    }
  }
}

final followupRepositoryProvider = Provider<FollowupRepository>((ref) {
  return FollowupRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final followupSummaryProvider = FutureProvider<FollowupSummary>((ref) {
  return ref.watch(followupRepositoryProvider).fetchSummary();
});
