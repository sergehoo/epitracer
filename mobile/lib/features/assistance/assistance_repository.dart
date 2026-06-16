import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/storage/local_cache.dart';

class AssistanceRepository {
  AssistanceRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  /// Crée une demande d'assistance. Si offline, sauvegarde en draft.
  Future<bool> createRequest({
    required String category,
    required String message,
    String? phone,
  }) async {
    final payload = {
      'category': category,
      'message': message,
      if (phone != null) 'phone': phone,
    };
    try {
      await _api.dio.post('/assistance/', data: payload);
      return true;
    } on DioException {
      final draftId = 'assist_${DateTime.now().millisecondsSinceEpoch}';
      await _cache.saveDraft(draftId, payload);
      return false;
    }
  }

  Future<bool> shareLocation({
    required double lat,
    required double lng,
    String? note,
  }) async {
    try {
      await _api.dio.post('/locations/', data: {
        'lat': lat,
        'lng': lng,
        if (note != null) 'note': note,
      });
      return true;
    } catch (_) {
      return false;
    }
  }
}

final assistanceRepositoryProvider = Provider<AssistanceRepository>((ref) {
  return AssistanceRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});
