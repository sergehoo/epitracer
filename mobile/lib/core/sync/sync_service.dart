import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../network/connectivity_service.dart';
import '../storage/local_cache.dart';

/// Service qui scrute le retour de connexion et tente de re-envoyer
/// tous les drafts stockés localement (check-ins, vaccinations, assistance…).
class SyncService {
  SyncService(this._ref);

  final Ref _ref;
  bool _running = false;

  /// Démarre la surveillance : à chaque transition offline→online,
  /// on essaie de vider la file des drafts.
  void start() {
    if (_running) return;
    _running = true;
    _ref.listen<AsyncValue<bool>>(isOnlineProvider, (prev, next) {
      final wasOffline = (prev?.asData?.value ?? true) == false;
      final isOnline = next.asData?.value ?? false;
      if (wasOffline && isOnline) {
        flushDrafts();
      }
    });
  }

  /// Tente d'envoyer tous les drafts. Supprime ceux qui réussissent.
  Future<int> flushDrafts() async {
    final cache = _ref.read(localCacheProvider);
    final api = _ref.read(apiClientProvider);
    final drafts = cache.getDrafts();
    var sent = 0;

    for (final entry in drafts.entries) {
      final id = entry.key;
      final data = entry.value;
      final endpoint = _endpointForDraft(id);
      if (endpoint == null) continue;

      try {
        await api.dio.post(endpoint, data: data);
        await cache.removeDraft(id);
        sent += 1;
      } catch (_) {
        // On laisse pour la prochaine tentative
        continue;
      }
    }
    return sent;
  }

  String? _endpointForDraft(String id) {
    if (id.startsWith('checkin_')) return '/checkins/';
    if (id.startsWith('vacc_draft_')) return '/vaccinations/';
    if (id.startsWith('assist_')) return '/assistance/';
    return null;
  }
}

final syncServiceProvider = Provider<SyncService>((ref) {
  final s = SyncService(ref);
  s.start();
  return s;
});
