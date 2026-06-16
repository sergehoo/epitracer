import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/push/push_service.dart';
import 'core/router/app_router.dart';
import 'core/storage/local_cache.dart';
import 'core/storage/secure_storage.dart';
import 'core/sync/sync_service.dart';
import 'core/theme/app_theme.dart';
import 'shared/widgets/app_lock_gate.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Force orientation portrait sur smartphone
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Charge les variables d'env depuis assets/.env
  try {
    await dotenv.load();
  } catch (_) {
    // Fichier .env optionnel — defaults dans le code
  }

  // Init Hive (cache offline + drafts)
  await initHive();

  // Init Firebase (FCM). Tolérant si la config GoogleService/firebase n'est pas
  // encore intégrée — on continue à booter l'app sans push.
  try {
    await Firebase.initializeApp();
  } catch (_) {
    debugPrint('[boot] Firebase non initialisé — push désactivé');
  }

  runApp(const ProviderScope(child: MonPassSanitaireApp()));
}

class MonPassSanitaireApp extends ConsumerStatefulWidget {
  const MonPassSanitaireApp({super.key});

  @override
  ConsumerState<MonPassSanitaireApp> createState() =>
      _MonPassSanitaireAppState();
}

class _MonPassSanitaireAppState extends ConsumerState<MonPassSanitaireApp> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      // Active le SyncService (drafts auto au retour de connexion)
      ref.read(syncServiceProvider);
      // Init FCM uniquement si l'utilisateur est connecté.
      final hasSession =
          await ref.read(secureStorageProvider).hasSession();
      if (hasSession) {
        try {
          await ref.read(pushServiceProvider).initialize();
        } catch (e) {
          debugPrint('[boot] PushService init error: $e');
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Mon Pass Sanitaire',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      routerConfig: router,
      locale: const Locale('fr', 'CI'),
      supportedLocales: const [
        Locale('fr', 'CI'),
        Locale('fr', 'FR'),
        Locale('en'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      builder: (context, child) =>
          AppLockGate(child: child ?? const SizedBox.shrink()),
    );
  }
}
