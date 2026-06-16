import 'dart:convert';

import 'package:cryptography/cryptography.dart' as crypto;
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../storage/local_cache.dart';

/// Résultat d'une vérification offline de QR pass.
class QrVerifyResult {
  QrVerifyResult({
    required this.valid,
    this.payload,
    this.reason,
    this.expired = false,
  });

  final bool valid;
  final Map<String, dynamic>? payload;
  final String? reason;
  final bool expired;
}

/// Récupère la clé publique Ed25519 du backend, la met en cache, et
/// vérifie une signature attachée à un QR code.
///
/// Format QR attendu (string décodé) :
/// {
///   "payload": { ...données pass... , "exp": "2026-06-15T..." },
///   "sig": "base64-url-safe Ed25519 signature de jsonEncode(payload)"
/// }
///
/// Le backend EpiTrace utilise déjà ce schéma via /api/v1/passes/public-key.pem
/// (PEM Ed25519) — on parse la partie base64 du PEM.
class QrVerifier {
  QrVerifier(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  static const _publicKeyCacheKey = 'ed25519_public_key_b64';
  static const _publicKeyEndpoint = '/passes/public-key.pem';

  Future<List<int>?> _loadPublicKey({bool forceRefresh = false}) async {
    if (!forceRefresh) {
      final cached = _cache.getJson(_publicKeyCacheKey);
      if (cached is String && cached.isNotEmpty) {
        return base64Decode(cached);
      }
    }
    try {
      final r = await _api.dio.get(
        _publicKeyEndpoint,
        options: Options(responseType: ResponseType.plain),
      );
      final pem = r.data.toString();
      final bytes = _extractPemBytes(pem);
      if (bytes != null) {
        await _cache.putJson(_publicKeyCacheKey, base64Encode(bytes));
        return bytes;
      }
    } catch (_) {/* network down — fall back to cache if any */}
    final cached = _cache.getJson(_publicKeyCacheKey);
    return cached is String ? base64Decode(cached) : null;
  }

  /// Parse un PEM SubjectPublicKeyInfo Ed25519 et en extrait les 32 bytes
  /// finaux (clé publique brute Ed25519).
  List<int>? _extractPemBytes(String pem) {
    final cleaned = pem
        .replaceAll(RegExp(r'-----BEGIN [^-]+-----'), '')
        .replaceAll(RegExp(r'-----END [^-]+-----'), '')
        .replaceAll(RegExp(r'\s'), '');
    if (cleaned.isEmpty) return null;
    try {
      final der = base64Decode(cleaned);
      // SPKI Ed25519 fait 44 bytes (12 header + 32 key). On prend les 32 derniers.
      if (der.length >= 32) {
        return der.sublist(der.length - 32);
      }
      return der;
    } catch (_) {
      return null;
    }
  }

  /// Vérifie un QR scanné. Retourne le résultat (valid, expired, payload).
  Future<QrVerifyResult> verify(String qrText) async {
    Map<String, dynamic> body;
    try {
      body = jsonDecode(qrText) as Map<String, dynamic>;
    } catch (_) {
      return QrVerifyResult(valid: false, reason: 'QR illisible (JSON invalide)');
    }

    final payload = body['payload'];
    final sigB64 = body['sig'];
    if (payload is! Map<String, dynamic> || sigB64 is! String) {
      return QrVerifyResult(valid: false, reason: 'Champs payload/sig manquants');
    }

    final pubKeyBytes = await _loadPublicKey();
    if (pubKeyBytes == null) {
      return QrVerifyResult(
        valid: false,
        reason: 'Clé publique introuvable (offline + cache vide)',
      );
    }

    final ed25519 = crypto.Ed25519();
    final publicKey = crypto.SimplePublicKey(
      pubKeyBytes,
      type: crypto.KeyPairType.ed25519,
    );
    final canonical = utf8.encode(jsonEncode(payload));
    final signatureBytes = _b64UrlSafeDecode(sigB64);
    if (signatureBytes == null) {
      return QrVerifyResult(valid: false, reason: 'Signature mal formée');
    }

    final ok = await ed25519.verify(
      canonical,
      signature: crypto.Signature(signatureBytes, publicKey: publicKey),
    );
    if (!ok) {
      return QrVerifyResult(
          valid: false, payload: payload, reason: 'Signature invalide');
    }

    // Vérifie l'expiration si présente
    bool expired = false;
    final exp = payload['exp'] ?? payload['expires_at'];
    if (exp is String) {
      final dt = DateTime.tryParse(exp);
      if (dt != null && DateTime.now().isAfter(dt)) {
        expired = true;
      }
    }

    return QrVerifyResult(
      valid: !expired,
      expired: expired,
      payload: payload,
      reason: expired ? 'Pass expiré' : null,
    );
  }

  List<int>? _b64UrlSafeDecode(String input) {
    try {
      String s = input.replaceAll('-', '+').replaceAll('_', '/');
      final pad = s.length % 4;
      if (pad != 0) s += '=' * (4 - pad);
      return base64Decode(s);
    } catch (_) {
      return null;
    }
  }
}

final qrVerifierProvider = Provider<QrVerifier>((ref) {
  return QrVerifier(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});
