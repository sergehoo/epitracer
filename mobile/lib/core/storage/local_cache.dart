import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

/// Cache local générique JSON-string (key → value) via Hive.
/// On stocke les réponses API en JSON brut pour rester découplé des
/// types Freezed (pas besoin d'enregistrer des adapters).
///
/// Boxes :
///   - `cache` : réponses API (passes, vaccinations, profile…)
///   - `meta`  : métadonnées (timestamps, sync queue)
///   - `drafts`: brouillons saisis offline (checkins, vaccinations en attente)
class LocalCache {
  LocalCache(this._cacheBox, this._metaBox, this._draftsBox);

  final Box<String> _cacheBox;
  final Box<String> _metaBox;
  final Box<String> _draftsBox;

  // ── Cache générique ──────────────────────────────────────────────
  Future<void> putJson(String key, dynamic value) async {
    await _cacheBox.put(key, jsonEncode(value));
    await _metaBox.put('${key}__ts', DateTime.now().toIso8601String());
  }

  dynamic getJson(String key) {
    final raw = _cacheBox.get(key);
    if (raw == null) return null;
    try {
      return jsonDecode(raw);
    } catch (_) {
      return null;
    }
  }

  DateTime? getJsonTimestamp(String key) {
    final raw = _metaBox.get('${key}__ts');
    if (raw == null) return null;
    return DateTime.tryParse(raw);
  }

  Future<void> remove(String key) async {
    await _cacheBox.delete(key);
    await _metaBox.delete('${key}__ts');
  }

  Future<void> clearAll() async {
    await _cacheBox.clear();
    await _metaBox.clear();
    await _draftsBox.clear();
  }

  // ── Brouillons offline (à synchroniser plus tard) ─────────────────
  Future<void> saveDraft(String id, dynamic payload) =>
      _draftsBox.put(id, jsonEncode(payload));

  Map<String, dynamic> getDrafts() {
    final out = <String, dynamic>{};
    for (final k in _draftsBox.keys) {
      try {
        out[k.toString()] = jsonDecode(_draftsBox.get(k.toString())!);
      } catch (_) {/* skip */}
    }
    return out;
  }

  Future<void> removeDraft(String id) => _draftsBox.delete(id);
}

/// Initialise Hive et ouvre les 3 boxes au démarrage de l'app.
Future<void> initHive() async {
  await Hive.initFlutter();
  await Hive.openBox<String>('cache');
  await Hive.openBox<String>('meta');
  await Hive.openBox<String>('drafts');
}

final localCacheProvider = Provider<LocalCache>((ref) {
  return LocalCache(
    Hive.box<String>('cache'),
    Hive.box<String>('meta'),
    Hive.box<String>('drafts'),
  );
});

// Clés standardisées
class CacheKeys {
  static const profile = 'profile';
  static const passes = 'passes';
  static const passDetail = 'pass';   // suffixé par /id
  static const vaccinations = 'vaccinations';
  static const followup = 'followup';
  static const notifications = 'notifications';

  static String passDetailKey(int id) => 'pass_$id';
}
