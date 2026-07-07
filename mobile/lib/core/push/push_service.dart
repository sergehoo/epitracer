import 'dart:io' show Platform;

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../router/app_router.dart';
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
///   - deep-link : tap sur une notif `data.type == "daily_checkin"` ouvre
///     l'écran [AppRoutes.checkin] (rappel sanitaire quotidien).
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

    // App ouverte (background → foreground via tap utilisateur)
    FirebaseMessaging.onMessageOpenedApp.listen(_handleOpenedMessage);

    // App lancée par le tap sur la notif (état terminated → foreground).
    // getInitialMessage() retourne le RemoteMessage si l'app a démarré
    // suite à un tap sur la notif, sinon null. On le traite après le
    // premier frame pour s'assurer que le GoRouter est prêt.
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      SchedulerBinding.instance.addPostFrameCallback((_) {
        _handleOpenedMessage(initial);
      });
    }

    await _syncToken();
    FirebaseMessaging.instance.onTokenRefresh.listen(_registerToken);
  }

  /// Route le tap sur la notification selon `data.type`.
  ///
  /// Pour le moment, un seul deep-link est géré : `daily_checkin` →
  /// écran de check-in quotidien. Tout autre type tombe sur le simple log
  /// et l'utilisateur arrive sur le dashboard par défaut.
  void _handleOpenedMessage(RemoteMessage msg) {
    debugPrint('[FCM tap] ${msg.messageId} data=${msg.data}');
    final type = msg.data['type']?.toString() ?? '';
    if (type == 'daily_checkin') {
      _goToCheckin();
    }
  }

  /// Navigation vers l'écran check-in en utilisant le GoRouter Riverpod.
  ///
  /// On utilise un post-frame callback pour ne pas tenter de naviguer
  /// avant que le widget tree (et donc le routeur) ne soit monté — utile
  /// quand la notif est ouverte depuis un état "terminated".
  void _goToCheckin() {
    SchedulerBinding.instance.addPostFrameCallback((_) {
      try {
        final router = _ref.read(routerProvider);
        // `go` pousse la destination en remplaçant la pile — l'utilisateur
        // peut revenir en arrière vers le dashboard normalement.
        router.go(AppRoutes.checkin);
      } catch (e) {
        debugPrint('[FCM tap] navigation error: $e');
      }
    });
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
