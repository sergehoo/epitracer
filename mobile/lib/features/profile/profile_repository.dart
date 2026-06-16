import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/user.dart';
import '../../core/storage/local_cache.dart';

class ProfileRepository {
  ProfileRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  /// Charge le profil utilisateur depuis l'API.
  /// Sur erreur réseau → retombe sur le cache local si disponible.
  Future<AppUser?> fetchProfile({bool forceRefresh = false}) async {
    if (!forceRefresh) {
      final cached = _cache.getJson(CacheKeys.profile);
      if (cached is Map<String, dynamic>) {
        // Retour cache immédiat + déclenche refresh background non-await
        _refreshInBackground();
        try {
          return AppUser.fromJson(_normalize(cached));
        } catch (_) {/* ignore */}
      }
    }
    return _refresh();
  }

  Future<AppUser?> _refresh() async {
    try {
      final r = await _api.dio.get('/profile/');
      final data = r.data as Map<String, dynamic>;
      await _cache.putJson(CacheKeys.profile, data);
      return AppUser.fromJson(_normalize(data));
    } on DioException {
      // Si offline, fallback cache
      final cached = _cache.getJson(CacheKeys.profile);
      if (cached is Map<String, dynamic>) {
        try {
          return AppUser.fromJson(_normalize(cached));
        } catch (_) {/* */}
      }
      return null;
    }
  }

  void _refreshInBackground() {
    _refresh();
  }

  /// Mapping snake_case → camelCase pour Freezed
  Map<String, dynamic> _normalize(Map<String, dynamic> raw) => {
        'id': raw['id'],
        'email': raw['email'] ?? '',
        'fullName': raw['full_name'] ?? '',
        'phone': raw['phone'] ?? '',
        'mfaEnabled': raw['mfa_enabled'] ?? false,
        'avatarUrl': raw['avatar_url'],
      };
}

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

/// Provider exposé aux UI : profil utilisateur courant (auto-cache).
final profileProvider = FutureProvider<AppUser?>((ref) {
  return ref.watch(profileRepositoryProvider).fetchProfile();
});
