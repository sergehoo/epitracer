import 'package:freezed_annotation/freezed_annotation.dart';

part 'vaccination.freezed.dart';
part 'vaccination.g.dart';

@freezed
class Vaccination with _$Vaccination {
  const factory Vaccination({
    required int id,
    @JsonKey(name: 'disease_code') required String diseaseCode,
    @JsonKey(name: 'disease_name') required String diseaseName,
    @JsonKey(name: 'vaccine_name') required String vaccineName,
    @JsonKey(name: 'manufacturer') String? manufacturer,
    @JsonKey(name: 'lot_number') String? lotNumber,
    @JsonKey(name: 'administered_at') required DateTime administeredAt,
    @JsonKey(name: 'next_dose_at') DateTime? nextDoseAt,
    @JsonKey(name: 'dose_number') @Default(1) int doseNumber,
    @JsonKey(name: 'total_doses') @Default(1) int totalDoses,
    @JsonKey(name: 'center_name') String? centerName,
    @JsonKey(name: 'country_code') @Default('CI') String countryCode,
    @JsonKey(name: 'certificate_pdf_url') String? certificatePdfUrl,
    @JsonKey(name: 'qr_payload') String? qrPayload,
    @Default(false) bool verified,
  }) = _Vaccination;

  factory Vaccination.fromJson(Map<String, dynamic> json) =>
      _$VaccinationFromJson(json);
}
