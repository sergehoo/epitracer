import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/health_facility.dart';
import '../../core/storage/local_cache.dart';
import 'health_facilities_data.dart';

class FacilitiesRepository {
  FacilitiesRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  static const _cacheKey = 'health_facilities';

  Future<List<HealthFacility>> fetchAll() async {
    try {
      final r = await _api.dio.get('/health-facilities/');
      final raw = r.data;
      final list = (raw is List ? raw : raw['results'] ?? []) as List;
      await _cache.putJson(_cacheKey, list);
      if (list.isEmpty) return kCIHealthFacilities;
      return list
          .whereType<Map<String, dynamic>>()
          .map(HealthFacility.fromJson)
          .toList();
    } on DioException {
      final cached = _cache.getJson(_cacheKey);
      if (cached is List && cached.isNotEmpty) {
        return cached
            .whereType<Map<String, dynamic>>()
            .map(HealthFacility.fromJson)
            .toList();
      }
      // Fallback ultime : dataset embarqué (toujours dispo)
      return kCIHealthFacilities;
    }
  }
}

final facilitiesRepositoryProvider = Provider<FacilitiesRepository>((ref) {
  return FacilitiesRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final facilitiesProvider = FutureProvider<List<HealthFacility>>((ref) {
  return ref.watch(facilitiesRepositoryProvider).fetchAll();
});
