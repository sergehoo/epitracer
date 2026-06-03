import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pretty_dio_logger/pretty_dio_logger.dart';

import '../storage/secure_storage.dart';

/// Client HTTP unique pour toutes les requêtes vers le backend EpiTrace.
/// Gère automatiquement :
///   - Bearer token d'accès depuis SecureStorage
///   - Refresh JWT en cas de 401 (1 retry max)
///   - Logger pretty en dev
class ApiClient {
  ApiClient(this._storage) {
    final baseUrl = dotenv.env['API_MOBILE_BASE_URL']
        ?? 'https://api.veillesanitaire.com/api/mobile';
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      contentType: Headers.jsonContentType,
      responseType: ResponseType.json,
      headers: {
        'Accept': 'application/json',
        'X-Client': 'mobile',
      },
    ));

    _dio.interceptors.add(_AuthInterceptor(_storage, _dio));

    if ((dotenv.env['DEBUG'] ?? 'false') == 'true') {
      _dio.interceptors.add(PrettyDioLogger(
        requestHeader: false,
        requestBody: true,
        responseBody: true,
        responseHeader: false,
        compact: true,
      ));
    }
  }

  late final Dio _dio;
  final SecureStorageService _storage;

  Dio get dio => _dio;
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this._storage, this._dio);

  final SecureStorageService _storage;
  final Dio _dio;
  bool _refreshing = false;

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    // Skip auth pour les endpoints publics
    if (options.extra['skipAuth'] == true) {
      return handler.next(options);
    }
    final token = await _storage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    // Tentative de refresh sur 401
    if (err.response?.statusCode == 401 && !_refreshing) {
      final refresh = await _storage.getRefreshToken();
      if (refresh != null && refresh.isNotEmpty) {
        _refreshing = true;
        try {
          // Endpoint refresh — partagé avec la web app (DRF SimpleJWT)
          final baseUrl = dotenv.env['API_BASE_URL']
              ?? 'https://api.veillesanitaire.com/api/v1';
          final response = await Dio().post(
            '$baseUrl/auth/refresh/',
            data: {'refresh': refresh},
          );
          final newAccess = response.data['access'] as String?;
          if (newAccess != null) {
            await _storage.saveAccessToken(newAccess);
            err.requestOptions.headers['Authorization'] = 'Bearer $newAccess';
            final retried = await _dio.fetch(err.requestOptions);
            _refreshing = false;
            return handler.resolve(retried);
          }
        } catch (_) {
          await _storage.clearSession();
        } finally {
          _refreshing = false;
        }
      }
    }
    handler.next(err);
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(secureStorageProvider));
});

/// Helper pour extraire un message d'erreur lisible depuis une DioException.
String extractDioError(Object e) {
  if (e is! DioException) return e.toString();
  final data = e.response?.data;
  if (data is Map) {
    if (data['detail'] != null) return data['detail'].toString();
    if (data['error'] is Map && data['error']['message'] != null) {
      return data['error']['message'].toString();
    }
    // Format DRF par champ
    final entries = data.entries.where((k) => k.key != 'error');
    if (entries.isNotEmpty) {
      final first = entries.first;
      final v = first.value;
      if (v is List && v.isNotEmpty) return '${first.key} : ${v.first}';
      return '${first.key} : $v';
    }
  }
  return e.message ?? 'Erreur réseau inconnue.';
}
