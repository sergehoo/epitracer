/// Vaccination — modèle plain Dart (sans Freezed).
class Vaccination {
  const Vaccination({
    required this.id,
    required this.diseaseCode,
    required this.diseaseName,
    required this.vaccineName,
    required this.administeredAt,
    this.manufacturer,
    this.lotNumber,
    this.nextDoseAt,
    this.doseNumber = 1,
    this.totalDoses = 1,
    this.centerName,
    this.countryCode = 'CI',
    this.certificatePdfUrl,
    this.qrPayload,
    this.verified = false,
  });

  final int id;
  final String diseaseCode;
  final String diseaseName;
  final String vaccineName;
  final String? manufacturer;
  final String? lotNumber;
  final DateTime administeredAt;
  final DateTime? nextDoseAt;
  final int doseNumber;
  final int totalDoses;
  final String? centerName;
  final String countryCode;
  final String? certificatePdfUrl;
  final String? qrPayload;
  final bool verified;

  factory Vaccination.fromJson(Map<String, dynamic> j) {
    return Vaccination(
      id: (j['id'] as num?)?.toInt() ?? 0,
      diseaseCode: (j['disease_code'] ?? '').toString(),
      diseaseName: (j['disease_name'] ?? j['disease_code'] ?? '').toString(),
      vaccineName: (j['vaccine_name'] ?? '').toString(),
      manufacturer: j['manufacturer']?.toString(),
      lotNumber: j['lot_number']?.toString(),
      administeredAt: _parse(j['administered_at']) ?? DateTime.now(),
      nextDoseAt: _parse(j['next_dose_at']),
      doseNumber: (j['dose_number'] as num?)?.toInt() ?? 1,
      totalDoses: (j['total_doses'] as num?)?.toInt() ?? 1,
      centerName: j['center_name']?.toString(),
      countryCode: (j['country_code'] ?? 'CI').toString(),
      certificatePdfUrl: j['certificate_pdf_url']?.toString(),
      qrPayload: j['qr_payload']?.toString(),
      verified: j['verified'] == true,
    );
  }

  static DateTime? _parse(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}
