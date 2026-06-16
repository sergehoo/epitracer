/// Carnet de santé complet d'un voyageur.
/// Sauvegardé côté backend mais également cacheable offline via Hive.
class MedicalRecord {
  const MedicalRecord({
    this.bloodType,
    this.heightCm,
    this.weightKg,
    this.allergies = const [],
    this.chronicConditions = const [],
    this.currentMedications = const [],
    this.previousSurgeries = const [],
    this.emergencyContacts = const [],
    this.organDonor = false,
    this.notes,
    this.updatedAt,
  });

  final String? bloodType;
  final int? heightCm;
  final double? weightKg;
  final List<String> allergies;
  final List<String> chronicConditions;
  final List<String> currentMedications;
  final List<String> previousSurgeries;
  final List<EmergencyContact> emergencyContacts;
  final bool organDonor;
  final String? notes;
  final DateTime? updatedAt;

  double? get bmi {
    if (heightCm == null || weightKg == null || heightCm! <= 0) return null;
    final m = heightCm! / 100.0;
    return weightKg! / (m * m);
  }

  String? get bmiCategory {
    final b = bmi;
    if (b == null) return null;
    if (b < 18.5) return 'Insuffisance pondérale';
    if (b < 25) return 'Corpulence normale';
    if (b < 30) return 'Surpoids';
    if (b < 35) return 'Obésité modérée';
    return 'Obésité sévère';
  }

  factory MedicalRecord.fromJson(Map<String, dynamic> j) {
    List<String> _strList(dynamic v) =>
        (v as List?)?.map((e) => e.toString()).toList() ?? const [];

    return MedicalRecord(
      bloodType: j['blood_type']?.toString(),
      heightCm: (j['height_cm'] as num?)?.toInt(),
      weightKg: (j['weight_kg'] as num?)?.toDouble(),
      allergies: _strList(j['allergies']),
      chronicConditions: _strList(j['chronic_conditions']),
      currentMedications: _strList(j['current_medications']),
      previousSurgeries: _strList(j['previous_surgeries']),
      emergencyContacts: (j['emergency_contacts'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(EmergencyContact.fromJson)
              .toList() ??
          const [],
      organDonor: j['organ_donor'] == true,
      notes: j['notes']?.toString(),
      updatedAt: j['updated_at'] != null
          ? DateTime.tryParse(j['updated_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'blood_type': bloodType,
        'height_cm': heightCm,
        'weight_kg': weightKg,
        'allergies': allergies,
        'chronic_conditions': chronicConditions,
        'current_medications': currentMedications,
        'previous_surgeries': previousSurgeries,
        'emergency_contacts':
            emergencyContacts.map((e) => e.toJson()).toList(),
        'organ_donor': organDonor,
        'notes': notes,
      };

  MedicalRecord copyWith({
    String? bloodType,
    int? heightCm,
    double? weightKg,
    List<String>? allergies,
    List<String>? chronicConditions,
    List<String>? currentMedications,
    List<String>? previousSurgeries,
    List<EmergencyContact>? emergencyContacts,
    bool? organDonor,
    String? notes,
  }) =>
      MedicalRecord(
        bloodType: bloodType ?? this.bloodType,
        heightCm: heightCm ?? this.heightCm,
        weightKg: weightKg ?? this.weightKg,
        allergies: allergies ?? this.allergies,
        chronicConditions: chronicConditions ?? this.chronicConditions,
        currentMedications: currentMedications ?? this.currentMedications,
        previousSurgeries: previousSurgeries ?? this.previousSurgeries,
        emergencyContacts: emergencyContacts ?? this.emergencyContacts,
        organDonor: organDonor ?? this.organDonor,
        notes: notes ?? this.notes,
        updatedAt: updatedAt,
      );
}

class EmergencyContact {
  const EmergencyContact({
    required this.name,
    required this.phone,
    this.relation,
  });

  final String name;
  final String phone;
  final String? relation;

  factory EmergencyContact.fromJson(Map<String, dynamic> j) =>
      EmergencyContact(
        name: (j['name'] ?? '').toString(),
        phone: (j['phone'] ?? '').toString(),
        relation: j['relation']?.toString(),
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'phone': phone,
        'relation': relation,
      };
}

const List<String> kBloodTypes = [
  'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'
];
