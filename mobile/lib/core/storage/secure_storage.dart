import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Wrapper autour de FlutterSecureStorage avec clés constantes typées.
/// Stocke uniquement les secrets (tokens JWT, PIN biométrique optionnel).
/// Pour les données métier (pass, vaccins) → utiliser Hive.
class SecureStorageService {
  SecureStorageService(this._storage);

  final FlutterSecureStorage _storage;

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userIdKey = 'user_id';
  static const _userEmailKey = 'user_email';
  static const _userFullNameKey = 'user_full_name';
  static const _publicIdKey = 'traveler_public_id';
  static const _pinKey = 'app_pin_hash';
  static const _biometricKey = 'biometric_enabled';

  Future<void> saveAccessToken(String token) =>
      _storage.write(key: _accessKey, value: token);

  Future<String?> getAccessToken() => _storage.read(key: _accessKey);

  Future<void> saveRefreshToken(String token) =>
      _storage.write(key: _refreshKey, value: token);

  Future<String?> getRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> saveUser({
    required String id,
    required String email,
    String fullName = '',
    String? publicId,
  }) async {
    await _storage.write(key: _userIdKey, value: id);
    await _storage.write(key: _userEmailKey, value: email);
    await _storage.write(key: _userFullNameKey, value: fullName);
    if (publicId != null && publicId.isNotEmpty) {
      await _storage.write(key: _publicIdKey, value: publicId);
    }
  }

  Future<Map<String, String?>> getUser() async => {
        'id': await _storage.read(key: _userIdKey),
        'email': await _storage.read(key: _userEmailKey),
        'full_name': await _storage.read(key: _userFullNameKey),
        'public_id': await _storage.read(key: _publicIdKey),
      };

  /// Identifiant public TRV-XXXX du voyageur (utilisé par les endpoints
  /// publics /api/v1/public/*). Disponible après vérification OTP.
  Future<String?> getPublicId() => _storage.read(key: _publicIdKey);

  Future<void> savePublicId(String publicId) =>
      _storage.write(key: _publicIdKey, value: publicId);

  Future<bool> hasSession() async {
    final access = await getAccessToken();
    return access != null && access.isNotEmpty;
  }

  Future<void> clearSession() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _userEmailKey);
    await _storage.delete(key: _userFullNameKey);
  }

  // PIN local optionnel (hashé SHA-256)
  Future<void> savePinHash(String hash) =>
      _storage.write(key: _pinKey, value: hash);

  Future<String?> getPinHash() => _storage.read(key: _pinKey);

  Future<void> setBiometricEnabled(bool enabled) =>
      _storage.write(key: _biometricKey, value: enabled.toString());

  Future<bool> isBiometricEnabled() async {
    final v = await _storage.read(key: _biometricKey);
    return v == 'true';
  }
}

final secureStorageProvider = Provider<SecureStorageService>((ref) {
  const options = AndroidOptions(encryptedSharedPreferences: true);
  return SecureStorageService(
    const FlutterSecureStorage(aOptions: options),
  );
});
