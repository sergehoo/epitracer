import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Service i18n minimaliste : map de clés → traductions par langue.
/// Pas de codegen, pas de ARB — facile à étendre vers Dioula/Baoulé/Bété
/// en ajoutant une entrée dans [_translations].
///
/// Usage :
///   final t = ref.watch(translateProvider);
///   Text(t('dashboard.greeting'))
class AppI18n {
  AppI18n(this._locale);

  static const String fr = 'fr';
  static const String en = 'en';
  static const String dyu = 'dyu';  // Dioula
  static const String bci = 'bci';  // Baoulé

  final String _locale;

  /// Retourne le label localisé pour la clé donnée.
  /// Fallback : français si la clé n'existe pas dans la langue active.
  String t(String key, [Map<String, String>? params]) {
    final lang = _translations[_locale] ?? _translations[fr]!;
    var text = lang[key] ?? _translations[fr]![key] ?? key;
    if (params != null) {
      params.forEach((k, v) {
        text = text.replaceAll('{$k}', v);
      });
    }
    return text;
  }

  static const Map<String, String> supportedLanguages = {
    fr: 'Français',
    en: 'English',
    dyu: 'Dioula',
    bci: 'Baoulé',
  };
}

/// Dictionnaires par langue. À enrichir au fil de l'eau.
/// Conventions de clés : `<feature>.<sub>` (ex. `dashboard.greeting`,
/// `auth.login_button`). Les valeurs peuvent contenir `{param}` substitué
/// via [AppI18n.t].
const Map<String, Map<String, String>> _translations = {
  AppI18n.fr: {
    // ── Common ──────────────────────────────────────────────────────
    'common.ok': 'OK',
    'common.cancel': 'Annuler',
    'common.save': 'Enregistrer',
    'common.close': 'Fermer',
    'common.loading': 'Chargement…',
    'common.error': 'Une erreur est survenue',
    'common.retry': 'Réessayer',
    'common.share': 'Partager',

    // ── Auth ────────────────────────────────────────────────────────
    'auth.login_title': 'Mon Pass Sanitaire',
    'auth.login_subtitle': 'République de Côte d\'Ivoire — INHP',
    'auth.passport': 'Numéro de passeport',
    'auth.phone': 'Téléphone (+225 …)',
    'auth.or': 'OU',
    'auth.request_otp': 'Recevoir un code SMS',
    'auth.validate': 'Valider',
    'auth.agent_inhp': 'Je suis agent INHP',

    // ── Dashboard ───────────────────────────────────────────────────
    'dashboard.greet_morning': 'Bonjour',
    'dashboard.greet_afternoon': 'Bon après-midi',
    'dashboard.greet_evening': 'Bonsoir',
    'dashboard.status_title': 'Statut sanitaire',
    'dashboard.status_ok': 'Vous êtes en règle',
    'dashboard.status_followup': 'Suivi en cours',
    'dashboard.section_services': 'Mes services',
    'dashboard.section_learn': 'Apprendre la santé',

    // ── Services ────────────────────────────────────────────────────
    'svc.my_passes': 'Mes pass',
    'svc.vaccinations': 'Vaccinations',
    'svc.followup': 'Suivi 21j',
    'svc.medical': 'Carnet santé',
    'svc.map': 'Centres santé',
    'svc.assistance': 'Assistance',
    'svc.family': 'Ma famille',
    'svc.learn': 'Apprendre',
    'svc.teleconsult': 'Téléconsultation',

    // ── Settings ────────────────────────────────────────────────────
    'settings.title': 'Paramètres',
    'settings.language': 'Langue',
    'settings.biometric': 'Verrouillage biométrique',
    'settings.notifications': 'Notifications',
    'settings.about': 'À propos',
    'settings.logout': 'Se déconnecter',
  },

  AppI18n.en: {
    'common.ok': 'OK',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.close': 'Close',
    'common.loading': 'Loading…',
    'common.error': 'An error occurred',
    'common.retry': 'Retry',
    'common.share': 'Share',

    'auth.login_title': 'My Health Pass',
    'auth.login_subtitle': 'Republic of Côte d\'Ivoire — INHP',
    'auth.passport': 'Passport number',
    'auth.phone': 'Phone (+225 …)',
    'auth.or': 'OR',
    'auth.request_otp': 'Receive SMS code',
    'auth.validate': 'Verify',
    'auth.agent_inhp': 'I am an INHP agent',

    'dashboard.greet_morning': 'Good morning',
    'dashboard.greet_afternoon': 'Good afternoon',
    'dashboard.greet_evening': 'Good evening',
    'dashboard.status_title': 'Health status',
    'dashboard.status_ok': 'You are in good standing',
    'dashboard.status_followup': 'Follow-up in progress',
    'dashboard.section_services': 'My services',
    'dashboard.section_learn': 'Health education',

    'svc.my_passes': 'My passes',
    'svc.vaccinations': 'Vaccinations',
    'svc.followup': '21-day follow-up',
    'svc.medical': 'Health record',
    'svc.map': 'Health centers',
    'svc.assistance': 'Assistance',
    'svc.family': 'My family',
    'svc.learn': 'Learn',
    'svc.teleconsult': 'Teleconsultation',

    'settings.title': 'Settings',
    'settings.language': 'Language',
    'settings.biometric': 'Biometric lock',
    'settings.notifications': 'Notifications',
    'settings.about': 'About',
    'settings.logout': 'Sign out',
  },

  // Dioula / Baoulé : placeholders à remplir avec un locuteur natif.
  // Pour l'instant on délègue au français — fallback automatique.
  AppI18n.dyu: {},
  AppI18n.bci: {},
};

// ─── Riverpod providers ──────────────────────────────────────────────

const _kLocaleKey = 'app_locale';

/// Notifier de locale — API Notifier compatible Riverpod 2.x et 3.x.
class LocaleNotifier extends Notifier<String> {
  @override
  String build() {
    // Hydrate depuis SharedPreferences au build (fire-and-forget).
    _hydrate();
    return AppI18n.fr;
  }

  Future<void> _hydrate() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_kLocaleKey);
      if (saved != null && AppI18n.supportedLanguages.containsKey(saved)) {
        state = saved;
      }
    } catch (_) {/* silencieux */}
  }

  Future<void> setLocale(String locale) async {
    if (!AppI18n.supportedLanguages.containsKey(locale)) return;
    state = locale;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kLocaleKey, locale);
    } catch (_) {/* silencieux */}
  }
}

/// Provider de la locale courante.
final localeProvider = NotifierProvider<LocaleNotifier, String>(
  LocaleNotifier.new,
);

/// Helper d'appel court : `setLocale(ref, AppI18n.en)`.
Future<void> setLocale(WidgetRef ref, String locale) =>
    ref.read(localeProvider.notifier).setLocale(locale);

/// Provider exposant directement la fonction de traduction `t(key)`.
final translateProvider =
    Provider<String Function(String, [Map<String, String>?])>((ref) {
  final locale = ref.watch(localeProvider);
  final i18n = AppI18n(locale);
  return i18n.t;
});
