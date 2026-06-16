import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/health_pass.dart';
import '../../core/storage/local_cache.dart';

class PassesRepository {
  PassesRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  Future<List<HealthPass>> fetchPasses() async {
    try {
      final r = await _api.dio.get('/passes/');
      final raw = r.data;
      final list = (raw is List ? raw : raw['results'] ?? []) as List;
      final passes = list
          .whereType<Map<String, dynamic>>()
          .map(HealthPass.fromJson)
          .toList();
      await _cache.putJson(CacheKeys.passes, list);
      return passes;
    } on DioException {
      return _fromCacheList(CacheKeys.passes);
    }
  }

  Future<HealthPass?> fetchPass(int id) async {
    try {
      final r = await _api.dio.get('/passes/$id/');
      final data = r.data as Map<String, dynamic>;
      await _cache.putJson(CacheKeys.passDetailKey(id), data);
      return HealthPass.fromJson(data);
    } on DioException {
      final cached = _cache.getJson(CacheKeys.passDetailKey(id));
      if (cached is Map<String, dynamic>) return HealthPass.fromJson(cached);
      return null;
    }
  }

  /// Importe un pass scanné depuis QR
  Future<HealthPass?> importQr(String qrPayload) async {
    final r = await _api.dio.post('/qr/import/', data: {'qr_payload': qrPayload});
    if (r.statusCode == 200) {
      return HealthPass.fromJson(r.data as Map<String, dynamic>);
    }
    return null;
  }

  List<HealthPass> _fromCacheList(String key) {
    final cached = _cache.getJson(key);
    if (cached is List) {
      return cached
          .whereType<Map<String, dynamic>>()
          .map(HealthPass.fromJson)
          .toList();
    }
    return [];
  }
}

final passesRepositoryProvider = Provider<PassesRepository>((ref) {
  return PassesRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final passesProvider = FutureProvider<List<HealthPass>>((ref) {
  return ref.watch(passesRepositoryProvider).fetchPasses();
});

final passByIdProvider = FutureProvider.family<HealthPass?, int>((ref, id) {
  return ref.watch(passesRepositoryProvider).fetchPass(id);
});
