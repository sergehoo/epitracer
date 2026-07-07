import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'followup_repository.dart';

/// Service de pings de localisation pour le suivi 21 jours.
///
/// Le service envoie un ping toutes les 4 heures TANT QUE :
///   - l'utilisateur est dans l'app (foreground), ET
///   - il a explicitement consenti au scope `geolocation` (RGPD).
///
/// Note importante — pas de tracking caché :
///   * pas de service Android "foreground" persistant ;
///   * pas de WorkManager planifié à l'avance ;
///   * arrêt immédiat dès retrait du consentement.
///
/// C'est un compromis assumé : on perd la couverture quand l'app est
/// fermée, mais on respecte strictement le RGPD (collecte minimale,
/// finalité explicite, retrait effectif).
///
/// Le dernier timestamp de ping est persisté dans SharedPreferences pour
/// éviter de spammer le serveur si l'app est rouverte fréquemment.
class LocationPingService {
  LocationPingService(this._repo);

  static const Duration _interval = Duration(hours: 4);
  static const String _lastPingKey = 'followup_last_location_ping_ts';

  final FollowupRepository _repo;
  Timer? _timer;
  bool _running = false;

  bool get isRunning => _running;

  /// Démarre le service si pas déjà actif. Vérifie permission + consent.
  Future<void> start() async {
    if (_running) return;

    // Vérification consentement local (le serveur revérifie côté API).
    final pid = await _repo.getPublicId();
    if (pid == null || pid.isEmpty) {
      debugPrint('[LocationPing] Pas de public_id — service inactif.');
      return;
    }

    // Permission OS
    final hasPermission = await _ensurePermission();
    if (!hasPermission) {
      debugPrint('[LocationPing] Permission refusée — service inactif.');
      return;
    }

    _running = true;

    // Première vérification au démarrage : si > 4h depuis le dernier ping,
    // on en envoie un tout de suite, puis on planifie les suivants.
    final shouldPingNow = await _shouldPingNow();
    if (shouldPingNow) {
      await _tryPing();
    }
    _timer = Timer.periodic(_interval, (_) => _tryPing());
    debugPrint('[LocationPing] Démarré (intervalle: ${_interval.inHours}h).');
  }

  Future<void> stop() async {
    _timer?.cancel();
    _timer = null;
    _running = false;
    debugPrint('[LocationPing] Arrêté.');
  }

  Future<bool> _ensurePermission() async {
    try {
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) return false;
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      return perm == LocationPermission.always ||
          perm == LocationPermission.whileInUse;
    } catch (e) {
      debugPrint('[LocationPing] Erreur permission: $e');
      return false;
    }
  }

  Future<bool> _shouldPingNow() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final last = prefs.getInt(_lastPingKey);
      if (last == null) return true;
      final since = DateTime.now().millisecondsSinceEpoch - last;
      return since >= _interval.inMilliseconds;
    } catch (_) {
      return true;
    }
  }

  Future<void> _tryPing() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 20),
        ),
      );
      final ok = await _repo.sendLocationPing(
        latitude: pos.latitude,
        longitude: pos.longitude,
        accuracyM: pos.accuracy,
        eventType: 'manual_share',
      );
      if (ok) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt(
          _lastPingKey,
          DateTime.now().millisecondsSinceEpoch,
        );
        // On ne logue PAS les coordonnées (privacy by design).
        debugPrint('[LocationPing] Ping envoyé.');
      }
    } catch (e) {
      debugPrint('[LocationPing] Échec ping: ${e.runtimeType}');
    }
  }
}

final locationPingServiceProvider = Provider<LocationPingService>((ref) {
  final svc = LocationPingService(ref.watch(followupRepositoryProvider));
  ref.onDispose(svc.stop);
  return svc;
});
