/// Repository pour le DynamicForm runner (Phase 8B).
/// - fetchSchema(code) → GET /forms/<code>/schema/
/// - submit(code, answers, signature) → POST /forms/<code>/submissions/
/// - draft local (Hive, box `drafts`) auto-sauvé
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/storage/local_cache.dart';
import 'runner_models.dart';

/// Préfixe de clé Hive pour les brouillons par form code.
String _draftKey(String code) => 'form_runner_draft_$code';

class FormRunnerRepository {
  FormRunnerRepository(this._api, this._cache);

  final ApiClient _api;
  final LocalCache _cache;

  /// Récupère le schéma complet d'un formulaire dynamique.
  ///
  /// Endpoint public (AllowAny) — on désactive l'Authorization Bearer
  /// pour éviter qu'un token expiré ne casse l'appel.
  Future<FormSchema> fetchSchema(String code) async {
    final r = await _api.dio.get(
      '/forms/$code/schema/',
      options: Options(extra: {'skipAuth': true}),
    );
    final data = r.data;
    if (data is! Map<String, dynamic>) {
      throw const FormatException('Schéma de formulaire invalide.');
    }
    return FormSchema.fromJson(data);
  }

  /// Soumet le formulaire au backend. answers = {field_code: value}.
  /// `signature` est une data-URL `data:image/png;base64,...` ou null.
  Future<SubmissionResult> submit(
    String code, {
    required Map<String, dynamic> answers,
    String? signatureDataUrl,
  }) async {
    final body = <String, dynamic>{
      'answers': answers,
      if (signatureDataUrl != null && signatureDataUrl.isNotEmpty)
        'signature': signatureDataUrl,
    };
    final r = await _api.dio.post(
      '/forms/$code/submissions/',
      data: body,
      options: Options(extra: {'skipAuth': true}),
    );
    final data = r.data;
    if (data is! Map<String, dynamic>) {
      throw const FormatException('Réponse de soumission invalide.');
    }
    // Brouillon → on l'efface dès que le serveur a accepté la fiche.
    await clearDraft(code);
    return SubmissionResult.fromJson(data);
  }

  // ── Brouillons offline ──────────────────────────────────────────
  Future<void> saveDraft(String code, Map<String, dynamic> answers,
      {int sectionIndex = 0}) async {
    await _cache.saveDraft(_draftKey(code), {
      'answers': answers,
      'section_index': sectionIndex,
      'updated_at': DateTime.now().toIso8601String(),
    });
  }

  Map<String, dynamic>? loadDraft(String code) {
    final drafts = _cache.getDrafts();
    final raw = drafts[_draftKey(code)];
    if (raw is Map<String, dynamic>) return raw;
    return null;
  }

  Future<void> clearDraft(String code) =>
      _cache.removeDraft(_draftKey(code));
}

final formRunnerRepositoryProvider = Provider<FormRunnerRepository>((ref) {
  return FormRunnerRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
  );
});

/// FutureProvider famille pour récupérer un schéma par code de formulaire.
final formSchemaProvider =
    FutureProvider.family<FormSchema, String>((ref, code) {
  return ref.watch(formRunnerRepositoryProvider).fetchSchema(code);
});
