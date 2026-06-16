/// Utilisateur authentifié — modèle plain Dart (sans Freezed).
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    this.fullName = '',
    this.phone = '',
    this.mfaEnabled = false,
    this.avatarUrl,
  });

  final int id;
  final String email;
  final String fullName;
  final String phone;
  final bool mfaEnabled;
  final String? avatarUrl;

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: (json['id'] as num?)?.toInt() ?? 0,
      email: (json['email'] ?? '').toString(),
      fullName:
          (json['fullName'] ?? json['full_name'] ?? '').toString(),
      phone: (json['phone'] ?? '').toString(),
      mfaEnabled:
          json['mfaEnabled'] == true || json['mfa_enabled'] == true,
      avatarUrl: json['avatarUrl']?.toString() ??
          json['avatar_url']?.toString(),
    );
  }
}
