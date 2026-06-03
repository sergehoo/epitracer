import 'package:freezed_annotation/freezed_annotation.dart';

part 'followup_checkin.freezed.dart';
part 'followup_checkin.g.dart';

@freezed
class CheckinPayload with _$CheckinPayload {
  const factory CheckinPayload({
    @JsonKey(name: 'feeling_well') @Default(true) bool feelingWell,
    @Default(false) bool fever,
    @JsonKey(name: 'unusual_fatigue') @Default(false) bool unusualFatigue,
    @Default(false) bool headache,
    @JsonKey(name: 'muscle_pain') @Default(false) bool musclePain,
    @JsonKey(name: 'vomiting_or_diarrhea') @Default(false) bool vomitingOrDiarrhea,
    @JsonKey(name: 'unexplained_bleeding') @Default(false) bool unexplainedBleeding,
    @JsonKey(name: 'wants_contact') @Default(false) bool wantsContact,
    @JsonKey(name: 'latitude') double? latitude,
    @JsonKey(name: 'longitude') double? longitude,
    @JsonKey(name: 'note') @Default('') String note,
  }) = _CheckinPayload;

  factory CheckinPayload.fromJson(Map<String, dynamic> json) =>
      _$CheckinPayloadFromJson(json);
}

@freezed
class FollowupDay with _$FollowupDay {
  const factory FollowupDay({
    required int day,
    required DateTime date,
    @Default(false) bool checkedIn,
    @Default(false) bool hadSymptoms,
  }) = _FollowupDay;

  factory FollowupDay.fromJson(Map<String, dynamic> json) =>
      _$FollowupDayFromJson(json);
}
