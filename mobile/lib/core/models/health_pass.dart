import 'package:freezed_annotation/freezed_annotation.dart';

part 'health_pass.freezed.dart';
part 'health_pass.g.dart';

enum PassStatus {
  @JsonValue('active')
  active,
  @JsonValue('expired')
  expired,
  @JsonValue('revoked')
  revoked,
  @JsonValue('pending')
  pending,
}

@freezed
class HealthPass with _$HealthPass {
  const HealthPass._();

  const factory HealthPass({
    required int id,
    @JsonKey(name: 'pass_number') required String passNumber,
    @JsonKey(name: 'public_id') required String publicId,
    @Default(PassStatus.active) PassStatus status,
    @JsonKey(name: 'disease_code') @Default('EBOLA') String diseaseCode,
    @JsonKey(name: 'disease_name') @Default('Ebola') String diseaseName,
    @JsonKey(name: 'traveler_full_name') @Default('') String travelerFullName,
    @JsonKey(name: 'entry_point_name') String? entryPointName,
    @JsonKey(name: 'issued_at') required DateTime issuedAt,
    @JsonKey(name: 'expires_at') required DateTime expiresAt,
    @JsonKey(name: 'qr_payload') @Default('') String qrPayload,
    @JsonKey(name: 'pdf_url') String? pdfUrl,
  }) = _HealthPass;

  factory HealthPass.fromJson(Map<String, dynamic> json) => _$HealthPassFromJson(json);

  bool get isExpired => DateTime.now().isAfter(expiresAt);
  bool get isExpiringSoon =>
      !isExpired && expiresAt.difference(DateTime.now()).inDays < 3;
  bool get isValid => status == PassStatus.active && !isExpired;
}
