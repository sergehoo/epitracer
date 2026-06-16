import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/storage/secure_storage.dart';

class VoyageurAuthRepository {
  VoyageurAuthRepository(this._api, this._storage);

  final ApiClient _api;
  final SecureStorageService _storage;

  /// Étape 1 — demande d'un code OTP par SMS au voyageur.
  Future<({bool ok, String phoneMasked, String? error})> requestOtp({
    String? passportNumber,
    String? phone,
  }) async {
    try {
      final r = await _api.dio.post(
        '/auth/voyageur/request-otp/',
        data: {
          if (passportNumber != null && passportNumber.isNotEmpty)
            'passport_number': passportNumber,
          if (phone != null && phone.isNotEmpty) 'phone': phone,
        },
        options: Options(extra: {'skipAuth': true}),
      );
      final data = r.data as Map<String, dynamic>;
      return (
        ok: data['ok'] == true,
        phoneMasked: (data['phone_masked'] ?? '').toString(),
        error: null,
      );
    } on DioException catch (e) {
      return (ok: false, phoneMasked: '', error: extractDioError(e));
    }
  }

  /// Étape 2 — vérification de l'OTP. Si OK, persiste les JWT.
  Future<({bool ok, String? error, Map<String, dynamic>? traveler})> verifyOtp({
    String? passportNumber,
    String? phone,
    required String code,
  }) async {
    try {
      final r = await _api.dio.post(
        '/auth/voyageur/verify-otp/',
        data: {
          if (passportNumber != null && passportNumber.isNotEmpty)
            'passport_number': passportNumber,
          if (phone != null && phone.isNotEmpty) 'phone': phone,
          'code': code,
        },
        options: Options(extra: {'skipAuth': true}),
      );
      final data = r.data as Map<String, dynamic>;
      final access = data['access']?.toString();
      final refresh = data['refresh']?.toString();
      if (access != null) await _storage.saveAccessToken(access);
      if (refresh != null) await _storage.saveRefreshToken(refresh);

      final traveler = (data['traveler'] as Map?)?.cast<String, dynamic>();
      if (traveler != null) {
        await _storage.saveUser(
          id: traveler['id']?.toString() ?? '',
          email: traveler['phone_masked']?.toString() ?? '',
          fullName: traveler['full_name']?.toString() ?? '',
        );
      }
      return (ok: true, error: null, traveler: traveler);
    } on DioException catch (e) {
      return (ok: false, error: extractDioError(e), traveler: null);
    }
  }
}

final voyageurAuthRepositoryProvider =
    Provider<VoyageurAuthRepository>((ref) {
  return VoyageurAuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(secureStorageProvider),
  );
});
