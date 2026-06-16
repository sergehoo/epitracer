import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import '../storage/secure_storage.dart';

/// Encapsule la lib `local_auth` pour faire de l'unlock biométrique.
class BiometricService {
  BiometricService(this._secure);

  final SecureStorageService _secure;
  final _auth = LocalAuthentication();

  /// Le device supporte-t-il un capteur biométrique configuré ?
  Future<bool> canUseBiometrics() async {
    try {
      final supported = await _auth.isDeviceSupported();
      final available = await _auth.canCheckBiometrics;
      return supported && available;
    } catch (_) {
      return false;
    }
  }

  /// Liste des biométries disponibles (face, fingerprint…).
  Future<List<BiometricType>> available() async {
    try {
      return await _auth.getAvailableBiometrics();
    } catch (_) {
      return const [];
    }
  }

  /// Demande l'authentification. Retourne `true` si l'utilisateur a réussi.
  /// Selon la version de local_auth, l'API d'options diverge ; on appelle ici
  /// la signature minimale qui marche partout, et on s'appuie sur les
  /// defaults raisonnables du plugin (sticky auth + dialog erreurs).
  Future<bool> authenticate(
      {String reason = 'Déverrouillez Mon Pass Sanitaire'}) async {
    try {
      return await _auth.authenticate(localizedReason: reason);
    } catch (_) {
      return false;
    }
  }

  Future<bool> isEnabled() => _secure.isBiometricEnabled();

  Future<void> setEnabled(bool value) => _secure.setBiometricEnabled(value);
}

final biometricServiceProvider = Provider<BiometricService>((ref) {
  return BiometricService(ref.watch(secureStorageProvider));
});
