import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class RegistrationForm {
  const RegistrationForm({
    required this.id,
    required this.code,
    required this.title,
    required this.description,
    required this.diseaseCode,
    required this.diseaseName,
    required this.isDefault,
    required this.webUrl,
  });

  final int? id;
  final String code;
  final String title;
  final String description;
  final String? diseaseCode;
  final String? diseaseName;
  final bool isDefault;
  final String webUrl;

  factory RegistrationForm.fromJson(Map<String, dynamic> j) {
    return RegistrationForm(
      id: (j['id'] as num?)?.toInt(),
      code: (j['code'] ?? '').toString(),
      title: (j['title'] ?? '').toString(),
      description: (j['description'] ?? '').toString(),
      diseaseCode: j['disease_code']?.toString(),
      diseaseName: j['disease_name']?.toString(),
      isDefault: j['is_default'] == true,
      webUrl: (j['web_url'] ?? '').toString(),
    );
  }
}

class RegistrationRepository {
  RegistrationRepository(this._api);
  final ApiClient _api;

  Future<List<RegistrationForm>> fetchActiveForms() async {
    try {
      final r = await _api.dio.get(
        '/registration/forms/',
        options: Options(extra: {'skipAuth': true}),
      );
      final list = (r.data['results'] as List?) ?? const [];
      return list
          .whereType<Map<String, dynamic>>()
          .map(RegistrationForm.fromJson)
          .toList();
    } on DioException {
      // Fallback : si l'endpoint n'est pas dispo (vieille version backend),
      // on retourne le formulaire générique pour ne pas bloquer le user.
      final fallbackBase = dotenv.env['PUBLIC_WEB_BASE_URL']
          ?? 'https://destinationci.com';
      return [
        RegistrationForm(
          id: null,
          code: 'default',
          title: 'Enregistrement voyageur — Côte d\'Ivoire',
          description:
              'Formulaire d\'enregistrement sanitaire à remplir avant ou à l\'arrivée.',
          diseaseCode: null,
          diseaseName: null,
          isDefault: true,
          webUrl: '$fallbackBase/voyageur',
        ),
      ];
    }
  }
}

final registrationRepositoryProvider = Provider<RegistrationRepository>((ref) {
  return RegistrationRepository(ref.watch(apiClientProvider));
});

final activeFormsProvider = FutureProvider<List<RegistrationForm>>((ref) {
  return ref.watch(registrationRepositoryProvider).fetchActiveForms();
});
