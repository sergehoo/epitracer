import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Environnement d'exécution déterminé au démarrage à partir de .env.
///
/// `ENVIRONMENT=staging` dans `.env` → [AppEnv.isStaging] = true.
/// Toute autre valeur (ou absence) → production.
///
/// Cette information sert à :
///   - Afficher un bandeau "STAGING" persistent (cf. StagingBanner)
///   - Activer du logging réseau verbeux en staging
///   - Eviter qu'un build staging soit confondu avec la prod en démo
enum AppEnvironment { production, staging }

class AppEnv {
  AppEnv._();

  /// Lit la variable ENVIRONMENT du .env chargé par flutter_dotenv.
  /// Doit être appelé APRÈS `await dotenv.load()` (dans main.dart).
  static AppEnvironment get current {
    final raw = (dotenv.env['ENVIRONMENT'] ?? 'production').toLowerCase().trim();
    if (raw == 'staging' || raw == 'stg' || raw == 'test') {
      return AppEnvironment.staging;
    }
    return AppEnvironment.production;
  }

  static bool get isStaging => current == AppEnvironment.staging;
  static bool get isProduction => current == AppEnvironment.production;

  /// Étiquette courte affichée dans le bandeau.
  static String get label =>
      isStaging ? 'STAGING' : 'PRODUCTION';

  /// URL de l'API mobile actuellement configurée — utile pour l'écran À propos.
  static String get apiBaseUrl =>
      dotenv.env['API_MOBILE_BASE_URL'] ??
      dotenv.env['API_BASE_URL'] ??
      'https://api.veillesanitaire.com/api/mobile';
}
