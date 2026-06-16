import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/medical_record.dart';
import '../../core/storage/local_cache.dart';

class MedicalRepository {
  MedicalRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  static const _cacheKey = 'medical_record';

  Future<MedicalRecord> fetch() async {
    try {
      final r = await _api.dio.get('/medical-record/');
      final data = r.data as Map<String, dynamic>;
      await _cache.putJson(_cacheKey, data);
      return MedicalRecord.fromJson(data);
    } on DioException {
      final cached = _cache.getJson(_cacheKey);
      if (cached is Map<String, dynamic>) {
        return MedicalRecord.fromJson(cached);
      }
      return const MedicalRecord();
    }
  }

  Future<bool> save(MedicalRecord record) async {
    final payload = record.toJson();
    // Sauvegarde immédiate du cache pour réactivité instant
    await _cache.putJson(_cacheKey, payload);
    try {
      await _api.dio.put('/medical-record/', data: payload);
      return true;
    } catch (_) {
      // Mode offline → draft persistant pour sync au retour
      await _cache.saveDraft('medical_$_cacheKey', payload);
      return false;
    }
  }
}

final medicalRepositoryProvider = Provider<MedicalRepository>((ref) {
  return MedicalRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final medicalRecordProvider = FutureProvider<MedicalRecord>((ref) {
  return ref.watch(medicalRepositoryProvider).fetch();
});
