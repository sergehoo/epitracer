/// Membre de la famille géré depuis le compte principal.
/// Chaque membre a son propre pass + suivi 21j côté backend.
class FamilyMember {
  const FamilyMember({
    required this.id,
    required this.fullName,
    required this.relation,
    this.dateOfBirth,
    this.phone,
    this.bloodType,
    this.isMinor = false,
    this.avatarUrl,
  });

  final String id;
  final String fullName;
  final FamilyRelation relation;
  final DateTime? dateOfBirth;
  final String? phone;
  final String? bloodType;
  final bool isMinor;
  final String? avatarUrl;

  int? get age {
    if (dateOfBirth == null) return null;
    final now = DateTime.now();
    var a = now.year - dateOfBirth!.year;
    if (now.month < dateOfBirth!.month ||
        (now.month == dateOfBirth!.month && now.day < dateOfBirth!.day)) {
      a -= 1;
    }
    return a;
  }

  String get initials {
    final parts = fullName.trim().split(RegExp(r'\s+'));
    String _first(String s) => s.isEmpty ? '' : s.substring(0, 1);
    if (parts.length == 1) return _first(parts.first).toUpperCase();
    return (_first(parts.first) + _first(parts.last)).toUpperCase();
  }

  factory FamilyMember.fromJson(Map<String, dynamic> j) => FamilyMember(
        id: (j['id'] ?? '').toString(),
        fullName: (j['full_name'] ?? '').toString(),
        relation: FamilyRelationX.fromString(
            j['relation']?.toString() ?? 'other'),
        dateOfBirth: j['date_of_birth'] != null
            ? DateTime.tryParse(j['date_of_birth'].toString())
            : null,
        phone: j['phone']?.toString(),
        bloodType: j['blood_type']?.toString(),
        isMinor: j['is_minor'] == true,
        avatarUrl: j['avatar_url']?.toString(),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'full_name': fullName,
        'relation': relation.code,
        'date_of_birth': dateOfBirth?.toIso8601String(),
        'phone': phone,
        'blood_type': bloodType,
        'is_minor': isMinor,
        'avatar_url': avatarUrl,
      };
}

enum FamilyRelation { self, spouse, child, parent, sibling, other }

extension FamilyRelationX on FamilyRelation {
  static FamilyRelation fromString(String raw) {
    switch (raw.toLowerCase()) {
      case 'self':
        return FamilyRelation.self;
      case 'spouse':
        return FamilyRelation.spouse;
      case 'child':
      case 'enfant':
        return FamilyRelation.child;
      case 'parent':
        return FamilyRelation.parent;
      case 'sibling':
      case 'frere':
      case 'soeur':
        return FamilyRelation.sibling;
      default:
        return FamilyRelation.other;
    }
  }

  String get code {
    switch (this) {
      case FamilyRelation.self:
        return 'self';
      case FamilyRelation.spouse:
        return 'spouse';
      case FamilyRelation.child:
        return 'child';
      case FamilyRelation.parent:
        return 'parent';
      case FamilyRelation.sibling:
        return 'sibling';
      case FamilyRelation.other:
        return 'other';
    }
  }

  String get label {
    switch (this) {
      case FamilyRelation.self:
        return 'Moi';
      case FamilyRelation.spouse:
        return 'Conjoint(e)';
      case FamilyRelation.child:
        return 'Enfant';
      case FamilyRelation.parent:
        return 'Parent';
      case FamilyRelation.sibling:
        return 'Frère / Sœur';
      case FamilyRelation.other:
        return 'Autre';
    }
  }
}
