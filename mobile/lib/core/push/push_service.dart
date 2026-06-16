import 'dart:io' show Platform;

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/notifications/notifications_repository.dart';

/// Handler obligatoire pour les notifications reçues quand l'app est terminée
/// ou en background. Doit être une top-level function annotée `@pragma`.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint(
      '[FCM bg] ${message.messageId} :: ${message.notification?.title}');
}

/// Service FCM minimal :
///   - permissions iOS / Android 13+
///   - background handler (top-level)
///   - foreground listener (log + on peut afficher via SnackBar côté UI)
///   - sync du token avec le backend EpiTrace
///
/// Note : pour les notifs in-app riches en foreground, on relancera plus tard
/// `flutter_local_notifications` quand l'API se sera stabilisée. En l'état,
/// Android affiche déjà l'icône dans la barre système via FCM natif.
class PushService {
  PushService(this._ref);

  final Ref _ref;
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;
    _initialized = true;

    final messaging = FirebaseMessaging.instance;

    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    FirebaseMessaging.onMessage.listen((msg) {
      debugPrint(
          '[FCM fg] ${msg.notification?.title} :: ${msg.notification?.body}');
      // Invalide la liste pour qu'un futur build affiche la nouvelle notif
      try {
        _ref.read(notificationsRepositoryProvider);
      } catch (_) {/* container non prêt */}
    });

    FirebaseMessaging.onMessageOpenedApp.listen((msg) {
      debugPrint('[FCM tap] ${msg.messageId}');
    });

    await _syncToken();
    FirebaseMessaging.instance.onTokenRefresh.listen(_registerToken);
  }

  Future<void> _syncToken() async {
    final token = await FirebaseMessaging.instance.getToken();
    if (token == null) return;
    await _registerToken(token);
  }

  Future<void> _registerToken(String token) async {
    final platform = Platform.isIOS ? 'ios' : 'android';
    await _ref
        .read(notificationsRepositoryProvider)
        .registerDevice(fcmToken: token, platform: platform);
  }

  /// Désinscription au logout — supprime le token côté FCM.
  Future<void> dispose() async {
    try {
      await FirebaseMessaging.instance.deleteToken();
    } catch (_) {/* ignore */}
  }
}

final pushServiceProvider = Provider<PushService>((ref) => PushService(ref));
