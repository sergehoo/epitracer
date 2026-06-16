import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/family_member.dart';
import '../../core/storage/local_cache.dart';

class FamilyRepository {
  FamilyRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  static const _cacheKey = 'family_members';
  static const _activeMemberKey = 'family_active_member_id';

  Future<List<FamilyMember>> fetchAll() async {
    try {
      final r = await _api.dio.get('/family/');
      final raw = r.data;
      final list = (raw is List ? raw : raw['results'] ?? []) as List;
      await _cache.putJson(_cacheKey, list);
      return list
          .whereType<Map<String, dynamic>>()
          .map(FamilyMember.fromJson)
          .toList();
    } on DioException {
      final cached = _cache.getJson(_cacheKey);
      if (cached is List) {
        return cached
            .whereType<Map<String, dynamic>>()
            .map(FamilyMember.fromJson)
            .toList();
      }
      return const [];
    }
  }

  Future<FamilyMember?> create(FamilyMember m) async {
    try {
      final r = await _api.dio.post('/family/', data: m.toJson());
      return FamilyMember.fromJson(r.data as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<bool> remove(String id) async {
    try {
      await _api.dio.delete('/family/$id/');
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Membre actuellement sélectionné dans le switcher (persistant local).
  Future<String?> getActiveMemberId() async =>
      _cache.getJson(_activeMemberKey) as String?;

  Future<void> setActiveMemberId(String? id) async {
    if (id == null) {
      await _cache.remove(_activeMemberKey);
    } else {
      await _cache.putJson(_activeMemberKey, id);
    }
  }
}

final familyRepositoryProvider = Provider<FamilyRepository>((ref) {
  return FamilyRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

final familyProvider = FutureProvider<List<FamilyMember>>((ref) {
  return ref.watch(familyRepositoryProvider).fetchAll();
});

/// Membre actif sélectionné (id stocké dans Hive).
final activeMemberIdProvider = FutureProvider<String?>((ref) {
  return ref.watch(familyRepositoryProvider).getActiveMemberId();
});
