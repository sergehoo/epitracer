import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/models/user.dart';
import '../../core/storage/secure_storage.dart';

class AuthRepository {
  AuthRepository(this._api, this._storage);

  final ApiClient _api;
  final SecureStorageService _storage;

  /// Étape 1 : email + password.
  /// Si MFA requise → status=mfa_required, sinon tokens en main.
  Future<AuthLoginResult> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _api.dio.post(
        '/auth/login/',
        data: {'email': email, 'password': password},
        options: Options(extra: {'skipAuth': true}),
      );
      final data = response.data as Map<String, dynamic>;
      await _persistSession(data);
      return AuthLoginResult(success: true);
    } on DioException catch (e) {
      final body = e.response?.data;
      if (body is Map && body['mfa_required'] == true) {
        return AuthLoginResult(
          success: false,
          mfaRequired: true,
          emailMasked: body['email_masked']?.toString() ?? '',
        );
      }
      return AuthLoginResult(
        success: false,
        error: extractDioError(e),
      );
    }
  }

  /// Étape 2 : email + password + mfa_code (6 chiffres).
  Future<AuthLoginResult> verifyOtp({
    required String email,
    required String password,
    required String code,
  }) async {
    try {
      final response = await _api.dio.post(
        '/auth/login/',
        data: {'email': email, 'password': password, 'mfa_code': code},
        options: Options(extra: {'skipAuth': true}),
      );
      await _persistSession(response.data as Map<String, dynamic>);
      return AuthLoginResult(success: true);
    } on DioException catch (e) {
      return AuthLoginResult(success: false, error: extractDioError(e));
    }
  }

  /// Renvoyer un nouveau code OTP.
  Future<bool> resendOtp(String email) async {
    try {
      await _api.dio.post(
        '/auth/mfa/email/resend/',
        data: {'email': email},
        options: Options(extra: {'skipAuth': true}),
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() => _storage.clearSession();

  Future<AppUser?> fetchProfile() async {
    try {
      final r = await _api.dio.get('/auth/me/');
      return AppUser.fromJson(r.data as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> _persistSession(Map<String, dynamic> data) async {
    final access = data['access']?.toString();
    final refresh = data['refresh']?.toString();
    if (access != null) await _storage.saveAccessToken(access);
    if (refresh != null) await _storage.saveRefreshToken(refresh);

    final user = data['user'];
    if (user is Map<String, dynamic>) {
      await _storage.saveUser(
        id: user['id']?.toString() ?? '',
        email: user['email']?.toString() ?? '',
        fullName: user['full_name']?.toString() ?? '',
      );
    }
  }
}

class AuthLoginResult {
  AuthLoginResult({
    required this.success,
    this.mfaRequired = false,
    this.emailMasked = '',
    this.error = '',
  });

  final bool success;
  final bool mfaRequired;
  final String emailMasked;
  final String error;
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(secureStorageProvider),
  );
});
