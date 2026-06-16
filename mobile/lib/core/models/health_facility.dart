/// Établissement de santé en Côte d'Ivoire.
class HealthFacility {
  const HealthFacility({
    required this.id,
    required this.name,
    required this.type,
    required this.lat,
    required this.lng,
    required this.city,
    this.address,
    this.phone,
    this.openHours,
    this.hasEmergency = false,
    this.specialties = const [],
  });

  final String id;
  final String name;
  final FacilityType type;
  final double lat;
  final double lng;
  final String city;
  final String? address;
  final String? phone;
  final String? openHours;
  final bool hasEmergency;
  final List<String> specialties;

  factory HealthFacility.fromJson(Map<String, dynamic> j) => HealthFacility(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        type: FacilityTypeX.fromString(j['type']?.toString() ?? 'clinic'),
        lat: (j['lat'] as num?)?.toDouble() ?? 0,
        lng: (j['lng'] as num?)?.toDouble() ?? 0,
        city: (j['city'] ?? '').toString(),
        address: j['address']?.toString(),
        phone: j['phone']?.toString(),
        openHours: j['open_hours']?.toString(),
        hasEmergency: j['has_emergency'] == true,
        specialties: (j['specialties'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
      );
}

enum FacilityType { chu, hospital, dispensary, pharmacy, vaccinationCenter, clinic }

extension FacilityTypeX on FacilityType {
  static FacilityType fromString(String raw) {
    switch (raw.toLowerCase()) {
      case 'chu':
        return FacilityType.chu;
      case 'hospital':
        return FacilityType.hospital;
      case 'dispensary':
        return FacilityType.dispensary;
      case 'pharmacy':
        return FacilityType.pharmacy;
      case 'vaccination_center':
      case 'vaccination':
        return FacilityType.vaccinationCenter;
      default:
        return FacilityType.clinic;
    }
  }

  String get label {
    switch (this) {
      case FacilityType.chu:
        return 'CHU';
      case FacilityType.hospital:
        return 'Hôpital';
      case FacilityType.dispensary:
        return 'Dispensaire';
      case FacilityType.pharmacy:
        return 'Pharmacie';
      case FacilityType.vaccinationCenter:
        return 'Centre de vaccination';
      case FacilityType.clinic:
        return 'Clinique';
    }
  }
}
