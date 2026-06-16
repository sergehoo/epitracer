/// Pass sanitaire — modèle plain Dart (sans Freezed, donc sans codegen).
/// Pour les besoins du scaffold mobile on garde un POJO immuable + fromJson tolérant.
class HealthPass {
  const HealthPass({
    required this.id,
    required this.passNumber,
    required this.publicId,
    required this.status,
    required this.diseaseCode,
    required this.diseaseName,
    required this.travelerFullName,
    required this.issuedAt,
    required this.expiresAt,
    this.entryPointName,
    this.qrPayload = '',
    this.pdfUrl,
  });

  final int id;
  final String passNumber;
  final String publicId;
  final PassStatus status;
  final String diseaseCode;
  final String diseaseName;
  final String travelerFullName;
  final String? entryPointName;
  final DateTime issuedAt;
  final DateTime expiresAt;
  final String qrPayload;
  final String? pdfUrl;

  /// Alias rétro-compat utilisé par certaines vues — équivaut à [diseaseName].
  String get disease => diseaseName;

  bool get isExpired => DateTime.now().isAfter(expiresAt);
  bool get isExpiringSoon =>
      !isExpired && expiresAt.difference(DateTime.now()).inDays < 3;
  bool get isValid => status == PassStatus.active && !isExpired;

  factory HealthPass.fromJson(Map<String, dynamic> json) {
    return HealthPass(
      id: (json['id'] as num?)?.toInt() ?? 0,
      passNumber: (json['pass_number'] ?? json['passNumber'] ?? '').toString(),
      publicId: (json['public_id'] ?? json['publicId'] ?? '').toString(),
      status: PassStatusX.fromString(
          json['status']?.toString() ?? 'active'),
      diseaseCode:
          (json['disease_code'] ?? json['diseaseCode'] ?? 'EBOLA').toString(),
      diseaseName:
          (json['disease_name'] ?? json['diseaseName'] ?? 'Ebola').toString(),
      travelerFullName:
          (json['traveler_full_name'] ?? json['travelerFullName'] ?? '')
              .toString(),
      entryPointName: json['entry_point_name']?.toString() ??
          json['entryPointName']?.toString(),
      issuedAt: _parseDate(json['issued_at'] ?? json['issuedAt']) ??
          DateTime.now(),
      expiresAt: _parseDate(json['expires_at'] ?? json['expiresAt']) ??
          DateTime.now().add(const Duration(days: 21)),
      qrPayload: (json['qr_payload'] ?? json['qrPayload'] ?? '').toString(),
      pdfUrl: json['pdf_url']?.toString() ?? json['pdfUrl']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'pass_number': passNumber,
        'public_id': publicId,
        'status': status.name,
        'disease_code': diseaseCode,
        'disease_name': diseaseName,
        'traveler_full_name': travelerFullName,
        'entry_point_name': entryPointName,
        'issued_at': issuedAt.toIso8601String(),
        'expires_at': expiresAt.toIso8601String(),
        'qr_payload': qrPayload,
        'pdf_url': pdfUrl,
      };

  static DateTime? _parseDate(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}

enum PassStatus { active, expired, revoked, pending }

extension PassStatusX on PassStatus {
  static PassStatus fromString(String raw) {
    switch (raw.toLowerCase()) {
      case 'expired':
      case 'expiré':
        return PassStatus.expired;
      case 'revoked':
      case 'révoqué':
        return PassStatus.revoked;
      case 'pending':
      case 'en attente':
        return PassStatus.pending;
      default:
        return PassStatus.active;
    }
  }

  String get label {
    switch (this) {
      case PassStatus.active:
        return 'Actif';
      case PassStatus.expired:
        return 'Expiré';
      case PassStatus.revoked:
        return 'Révoqué';
      case PassStatus.pending:
        return 'En attente';
    }
  }
}
