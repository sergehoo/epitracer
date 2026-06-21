import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/storage/local_cache.dart';
import '../../core/storage/secure_storage.dart';

/// Version du texte de politique présenté à l'utilisateur. Doit rester
/// synchronisée avec frontend/lib/companion.ts (CONSENT_VERSION).
const String kConsentVersion = 'v1.0-2026-05';

/// Liste centralisée des symptômes affichés à l'utilisateur.
///
/// L'ordre, les clés et les libellés doivent rester en parité avec la
/// PWA /voyageur/suivi (frontend/app/(public)/voyageur/suivi/page.tsx —
/// constante SYMPTOM_KEYS). Toute évolution doit être faite des deux côtés.
class SymptomDef {
  const SymptomDef({
    required this.key,
    required this.label,
    required this.critical,
  });
  final String key;
  final String label;

  /// Si true, déclenche le bandeau rouge "Contactez le 143".
  final bool critical;
}

const List<SymptomDef> kSymptoms = [
  SymptomDef(key: 'fever', label: 'Fièvre', critical: false),
  SymptomDef(key: 'intense_fatigue', label: 'Fatigue inhabituelle', critical: false),
  SymptomDef(key: 'severe_headache', label: 'Maux de tête importants', critical: false),
  SymptomDef(
    key: 'muscle_joint_pain',
    label: 'Douleurs musculaires ou articulaires',
    critical: false,
  ),
  SymptomDef(
    key: 'sore_throat_or_abdominal',
    label: 'Mal à la gorge ou au ventre',
    critical: false,
  ),
  SymptomDef(
    key: 'diarrhea_nausea_vomiting',
    label: 'Diarrhée, nausées ou vomissements',
    critical: false,
  ),
  SymptomDef(
    key: 'unexplained_bleeding',
    label: 'Saignements inexpliqués',
    critical: true,
  ),
  SymptomDef(key: 'conjunctivitis', label: 'Conjonctivite (yeux rouges)', critical: true),
  SymptomDef(key: 'chest_pain', label: 'Douleur thoracique', critical: true),
];

/// Sévérité d'un symptôme — alignée sur le modèle DailyCheck côté backend.
enum SymptomSeverity { mild, moderate, severe }

extension SymptomSeverityX on SymptomSeverity {
  String get apiValue => switch (this) {
        SymptomSeverity.mild => 'mild',
        SymptomSeverity.moderate => 'moderate',
        SymptomSeverity.severe => 'severe',
      };
  String get label => switch (this) {
        SymptomSeverity.mild => 'Légère',
        SymptomSeverity.moderate => 'Modérée',
        SymptomSeverity.severe => 'Sévère',
      };
}

/// Une entrée de check-in renvoyée par le backend (PWA endpoint).
class CheckEntry {
  CheckEntry({
    required this.checkDate,
    required this.dayIndex,
    required this.hasSymptoms,
    this.temperatureCelsius,
    this.feeling,
    this.needsContact = false,
    this.positiveSymptoms = const [],
    this.notes = '',
    this.alertRaised = false,
  });

  factory CheckEntry.fromJson(Map<String, dynamic> j) => CheckEntry(
        checkDate: DateTime.tryParse(j['check_date']?.toString() ?? '') ??
            DateTime.now(),
        dayIndex: (j['day_index'] as num?)?.toInt() ?? 0,
        hasSymptoms: j['has_symptoms'] == true,
        temperatureCelsius: (j['temperature_celsius'] as num?)?.toDouble(),
        feeling: j['feeling']?.toString(),
        needsContact: j['needs_contact'] == true,
        positiveSymptoms: (j['positive_symptoms'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        notes: j['notes']?.toString() ?? '',
        alertRaised: j['alert_raised'] == true,
      );

  final DateTime checkDate;
  final int dayIndex;
  final bool hasSymptoms;
  final double? temperatureCelsius;
  final String? feeling;
  final bool needsContact;
  final List<String> positiveSymptoms;
  final String notes;
  final bool alertRaised;

  /// True si le voyageur a déclaré un symptôme critique au dernier check-in.
  bool get hasCriticalSymptom {
    final criticalKeys = kSymptoms
        .where((s) => s.critical)
        .map((s) => s.key)
        .toSet();
    return positiveSymptoms.any(criticalKeys.contains);
  }
}

/// Snapshot complet du suivi 21j tel que renvoyé par /public/follow-up/status/.
class FollowUpStatus {
  FollowUpStatus({
    required this.publicId,
    required this.fullName,
    required this.active,
    required this.dayIndex,
    required this.totalDays,
    this.startedOn,
    this.expectedEndOn,
    this.lastCheck,
    this.checks = const [],
    this.consents = const {},
    this.samu = '185',
    this.alloSante = '143',
    this.secours = '101',
  });

  factory FollowUpStatus.fromJson(Map<String, dynamic> j) {
    final traveler =
        (j['traveler'] as Map?)?.cast<String, dynamic>() ?? const {};
    final quarantine =
        (j['quarantine'] as Map?)?.cast<String, dynamic>() ?? const {};
    final consents =
        (j['consents'] as Map?)?.cast<String, dynamic>() ?? const {};
    final assistance =
        (j['assistance'] as Map?)?.cast<String, dynamic>() ?? const {};
    final lastCheckRaw = j['last_check'];
    final checksRaw = j['checks'] as List?;

    DateTime? parseDate(dynamic v) {
      if (v == null) return null;
      return DateTime.tryParse(v.toString());
    }

    return FollowUpStatus(
      publicId: traveler['public_id']?.toString() ?? '',
      fullName: traveler['full_name']?.toString() ?? '',
      active: quarantine['active'] == true,
      dayIndex: (quarantine['day_index'] as num?)?.toInt() ?? 0,
      totalDays: (quarantine['total_days'] as num?)?.toInt() ?? 20,
      startedOn: parseDate(quarantine['started_on']),
      expectedEndOn: parseDate(quarantine['expected_end_on']),
      lastCheck: lastCheckRaw is Map<String, dynamic>
          ? CheckEntry.fromJson(lastCheckRaw)
          : null,
      checks: checksRaw
              ?.whereType<Map>()
              .map((e) => CheckEntry.fromJson(e.cast<String, dynamic>()))
              .toList() ??
          const [],
      consents: consents.map(
        (k, v) => MapEntry(k.toString(), v == true),
      ),
      samu: assistance['samu']?.toString() ?? '185',
      alloSante: assistance['allo_sante']?.toString() ?? '143',
      secours: assistance['secours']?.toString() ?? '101',
    );
  }

  final String publicId;
  final String fullName;
  final bool active;

  /// Day index 0-based (0 = jour de l'arrivée).
  final int dayIndex;

  /// total_days = expected_end_on - started_on. 20 = 21 jours (J0..J20).
  final int totalDays;
  final DateTime? startedOn;
  final DateTime? expectedEndOn;
  final CheckEntry? lastCheck;
  final List<CheckEntry> checks;
  final Map<String, bool> consents;
  final String samu;
  final String alloSante;
  final String secours;

  /// Jour courant à afficher (1-based), borné dans [1..totalDays+1].
  int get currentDay => (dayIndex + 1).clamp(1, totalDays + 1);

  /// Nombre total de jours à afficher dans la roue (généralement 21).
  int get totalDaysDisplay => totalDays + 1;

  /// Jours restants avant la fin du suivi (>=0).
  int get daysRemaining {
    final r = totalDays - dayIndex;
    return r < 0 ? 0 : r;
  }

  bool get geolocationConsented => consents['geolocation'] == true;
  bool get pushConsented => consents['push'] == true;

  /// True si le dernier check-in contient au moins un symptôme critique
  /// (saignement, conjonctivite, douleur thoracique).
  bool get hasCriticalRecentSymptom =>
      lastCheck?.hasCriticalSymptom == true;
}

/// Payload envoyé à /public/checkin/.
class CheckinSubmission {
  CheckinSubmission({
    required this.publicId,
    required this.feeling,
    this.symptoms = const {},
    this.symptomSeverities = const {},
    this.temperatureCelsius,
    this.notes = '',
    this.needsContact = false,
    this.latitude,
    this.longitude,
    this.accuracyM,
  });

  /// 'ok' | 'symptom' | 'assistance'
  final String feeling;
  final String publicId;

  /// Pour chaque clé de [kSymptoms], true si symptôme déclaré.
  final Map<String, bool> symptoms;

  /// Sévérité optionnelle par clé.
  final Map<String, SymptomSeverity> symptomSeverities;
  final double? temperatureCelsius;
  final String notes;
  final bool needsContact;
  final double? latitude;
  final double? longitude;
  final double? accuracyM;

  Map<String, dynamic> toJson() {
    // Pour rester compatible avec la PWA, on n'envoie au backend qu'un
    // booléen par symptôme. La sévérité est ajoutée dans `notes` comme
    // texte structuré pour ne rien perdre côté audit médical, en attendant
    // une évolution du serializer côté backend.
    final positives = <String, bool>{
      for (final e in symptoms.entries)
        if (e.value) e.key: true,
    };
    final severityNote = symptomSeverities.entries
        .where((e) => symptoms[e.key] == true)
        .map((e) => '${e.key}:${e.value.apiValue}')
        .join(';');
    final mergedNotes = [
      if (notes.trim().isNotEmpty) notes.trim(),
      if (severityNote.isNotEmpty) '[sev] $severityNote',
    ].join('\n');

    return {
      'public_id': publicId,
      'feeling': feeling,
      'symptoms': positives,
      'temperature_celsius': temperatureCelsius,
      'notes': mergedNotes,
      'needs_contact': needsContact,
      'latitude': latitude,
      'longitude': longitude,
      'accuracy_m': accuracyM,
    };
  }
}

class CheckinResult {
  CheckinResult({
    required this.ok,
    required this.message,
    this.alertCreated = false,
    this.alertSeverity,
    this.locationRecorded = false,
    this.offlineDraft = false,
  });

  final bool ok;
  final String message;
  final bool alertCreated;
  final String? alertSeverity;
  final bool locationRecorded;

  /// True si la requête a échoué (offline) et qu'on a stocké un brouillon.
  final bool offlineDraft;
}

/// ============================================================================
/// Compatibilité — résumé minimal renvoyé par /api/mobile/followups/.
///
/// Reste utilisé en fallback quand le voyageur n'a pas de public_id (ex :
/// agent INHP qui consulte l'app mobile depuis son compte staff).
/// ============================================================================
class FollowupSummary {
  FollowupSummary({
    required this.active,
    required this.day,
    required this.totalDays,
    required this.checkinTodayDone,
    this.startedAt,
    this.endsAt,
  });

  factory FollowupSummary.fromJson(Map<String, dynamic> j) => FollowupSummary(
        active: j['active'] == true,
        day: (j['day'] as num?)?.toInt() ?? 0,
        totalDays: (j['total_days'] as num?)?.toInt() ?? 21,
        checkinTodayDone: j['checkin_today_done'] == true,
        startedAt: j['started_at'] != null
            ? DateTime.tryParse(j['started_at'].toString())
            : null,
        endsAt: j['ends_at'] != null
            ? DateTime.tryParse(j['ends_at'].toString())
            : null,
      );

  final bool active;
  final int day;
  final int totalDays;
  final bool checkinTodayDone;
  final DateTime? startedAt;
  final DateTime? endsAt;
}

/// ============================================================================
/// Repository
/// ============================================================================
class FollowupRepository {
  FollowupRepository(this._api, this._cache, this._storage);

  final ApiClient _api;
  final LocalCache _cache;
  final SecureStorageService _storage;

  /// Renvoie l'URL absolue d'un endpoint public companion.
  ///
  /// L'`ApiClient` mobile pointe sur /api/mobile ; les endpoints companion
  /// sont sous /api/v1/public/. On reconstruit donc l'URL depuis
  /// `API_BASE_URL` (qui pointe sur /api/v1) avec un fallback raisonnable.
  String _publicUrl(String path) {
    final base = dotenv.env['API_BASE_URL'] ??
        'https://api.veillesanitaire.com/api/v1';
    final cleanBase = base.endsWith('/') ? base.substring(0, base.length - 1) : base;
    final cleanPath = path.startsWith('/') ? path : '/$path';
    return '$cleanBase$cleanPath';
  }

  /// Récupère le public_id du voyageur (depuis SecureStorage). Null si
  /// indisponible (par exemple : utilisateur agent INHP).
  Future<String?> getPublicId() => _storage.getPublicId();

  /// Statut complet du suivi 21 jours.
  ///
  /// La signature retourne nullable car un utilisateur agent INHP n'a pas
  /// de public_id ; dans ce cas on cascade vers [fetchSummary].
  Future<FollowUpStatus?> fetchFollowUpStatus({String? publicIdOverride}) async {
    final pid = publicIdOverride ?? await getPublicId();
    if (pid == null || pid.isEmpty) return null;
    try {
      final r = await _api.dio.get<Map<String, dynamic>>(
        _publicUrl('/public/follow-up/status/'),
        queryParameters: {'public_id': pid},
        options: Options(extra: {'skipAuth': true}),
      );
      final data = r.data ?? const {};
      await _cache.putJson('${CacheKeys.followup}_status', data);
      return FollowUpStatus.fromJson(data);
    } on DioException {
      final cached = _cache.getJson('${CacheKeys.followup}_status');
      if (cached is Map<String, dynamic>) {
        return FollowUpStatus.fromJson(cached);
      }
      return null;
    }
  }

  /// Résumé mobile-friendly (legacy, utilisé pour les comptes sans public_id).
  Future<FollowupSummary> fetchSummary() async {
    try {
      final r = await _api.dio.get<Map<String, dynamic>>('/followups/');
      final data = r.data ?? const {};
      await _cache.putJson(CacheKeys.followup, data);
      return FollowupSummary.fromJson(data);
    } on DioException {
      final cached = _cache.getJson(CacheKeys.followup);
      if (cached is Map<String, dynamic>) {
        return FollowupSummary.fromJson(cached);
      }
      return FollowupSummary(
        active: false,
        day: 0,
        totalDays: 21,
        checkinTodayDone: false,
      );
    }
  }

  /// Soumet un check-in (PWA endpoint /public/checkin/).
  Future<CheckinResult> submitPublicCheckin(CheckinSubmission p) async {
    try {
      final r = await _api.dio.post<Map<String, dynamic>>(
        _publicUrl('/public/checkin/'),
        data: p.toJson(),
        options: Options(extra: {'skipAuth': true}),
      );
      final data = r.data ?? const {};
      return CheckinResult(
        ok: data['ok'] == true,
        message: data['message']?.toString() ??
            'Merci pour votre check-in du jour.',
        alertCreated: data['alert_created'] == true,
        alertSeverity: data['alert_severity']?.toString(),
        locationRecorded: data['location_recorded'] == true,
      );
    } on DioException {
      // Offline → on stocke en draft pour sync ultérieur. Le SyncService
      // existant repassera les draft__checkin_* via /checkins/ (legacy).
      final draftId = 'checkin_public_${DateTime.now().millisecondsSinceEpoch}';
      await _cache.saveDraft(draftId, p.toJson());
      return CheckinResult(
        ok: false,
        offlineDraft: true,
        message:
            'Votre check-in sera envoyé automatiquement dès le retour de la connexion.',
      );
    }
  }

  /// Submit du check-in mobile (legacy, payload différent).
  /// Conservé pour compatibilité avec l'écran historique.
  Future<bool> submitCheckin(Map<String, dynamic> payload) async {
    try {
      await _api.dio.post('/checkins/', data: payload);
      return true;
    } on DioException {
      final draftId = 'checkin_${DateTime.now().millisecondsSinceEpoch}';
      await _cache.saveDraft(draftId, payload);
      return false;
    }
  }

  /// Enregistre / retire un consentement (RGPD).
  Future<bool> recordConsent({
    required String scope,
    required bool granted,
    String textExcerpt = '',
    String revocationReason = '',
    String? publicIdOverride,
  }) async {
    final pid = publicIdOverride ?? await getPublicId();
    if (pid == null || pid.isEmpty) return false;
    try {
      await _api.dio.post(
        _publicUrl('/public/consent/'),
        data: {
          'public_id': pid,
          'scope': scope,
          'granted': granted,
          'consent_version': kConsentVersion,
          'text_excerpt': textExcerpt,
          'revocation_reason': revocationReason,
        },
        options: Options(extra: {'skipAuth': true}),
      );
      return true;
    } on DioException {
      return false;
    }
  }

  /// Envoie un ping de localisation sur /public/location/ping/.
  ///
  /// `eventType` parmi : daily_checkin, manual_share, symptom_report,
  /// assistance_request, agent_visit (cf. backend LocationEventType).
  Future<bool> sendLocationPing({
    required double latitude,
    required double longitude,
    double? accuracyM,
    String eventType = 'manual_share',
    String? publicIdOverride,
  }) async {
    final pid = publicIdOverride ?? await getPublicId();
    if (pid == null || pid.isEmpty) return false;
    try {
      await _api.dio.post(
        _publicUrl('/public/location/ping/'),
        data: {
          'public_id': pid,
          'latitude': latitude,
          'longitude': longitude,
          'accuracy_m': accuracyM,
          'event_type': eventType,
          // Pas de UA navigateur côté mobile — on identifie l'appareil
          // de façon générique pour rester non-traçant. Aucun IMEI/IDFA.
          'device_info': 'mobile-app/flutter',
        },
        options: Options(extra: {'skipAuth': true}),
      );
      return true;
    } on DioException {
      return false;
    }
  }
}

/// ============================================================================
/// Providers Riverpod
/// ============================================================================
final followupRepositoryProvider = Provider<FollowupRepository>((ref) {
  return FollowupRepository(
    ref.watch(apiClientProvider),
    ref.watch(localCacheProvider),
    ref.watch(secureStorageProvider),
  );
});

/// Provider du statut complet (PWA endpoint).
final followUpStatusProvider = FutureProvider<FollowUpStatus?>((ref) {
  return ref.watch(followupRepositoryProvider).fetchFollowUpStatus();
});

/// Provider résumé legacy (utilisé en fallback uniquement).
final followupSummaryProvider = FutureProvider<FollowupSummary>((ref) {
  return ref.watch(followupRepositoryProvider).fetchSummary();
});
