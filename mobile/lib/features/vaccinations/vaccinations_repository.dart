import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/vaccination.dart';
import '../../core/storage/local_cache.dart';

class VaccinationsRepository {
  VaccinationsRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  Future<List<Vaccination>> fetchAll() async {
    try {
      final r = await _api.dio.get('/vaccinations/');
      final raw = r.data;
      final list = (raw is List ? raw : raw['results'] ?? []) as List;
      await _cache.putJson(CacheKeys.vaccinations, list);
      return list
          .whereType<Map<String, dynamic>>()
          .map(Vaccination.fromJson)
          .toList();
    } on DioException {
      final cached = _cache.getJson(CacheKeys.vaccinations);
      if (cached is List) {
        return cached
            .whereType<Map<String, dynamic>>()
            .map(Vaccination.fromJson)
            .toList();
      }
      return [];
    }
  }

  Future<Vaccination?> create(Map<String, dynamic> data) async {
    try {
      final r = await _api.dio.post('/vaccinations/', data: data);
      return Vaccination.fromJson(r.data as Map<String, dynamic>);
    } on DioException {
      // Sauvegarde en draft si offline
      final draftId = 'vacc_draft_${DateTime.now().millisecondsSinceEpoch}';
      await _cache.saveDraft(draftId, data);
      return null;
    }
  }

  Future<bool> delete(int id) async {
    try {
      await _api.dio.delete('/vaccinations/$id/');
      return true;
    } catch (_) {
      return false;
    }
  }
}

final vaccinationsRepositoryProvider = Provider<VaccinationsRepository>((ref) {
  return VaccinationsRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final vaccinationsProvider = FutureProvider<List<Vaccination>>((ref) {
  return ref.watch(vaccinationsRepositoryProvider).fetchAll();
});
