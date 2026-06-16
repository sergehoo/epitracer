import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mon_pass_sanitaire/core/api/api_client.dart';

DioException _err(dynamic data, {int status = 400}) {
  final req = RequestOptions(path: '/x');
  return DioException(
    requestOptions: req,
    response: Response(
      requestOptions: req,
      data: data,
      statusCode: status,
    ),
  );
}

void main() {
  test('renvoie detail si présent', () {
    expect(
      extractDioError(_err({'detail': 'Identifiants invalides.'})),
      'Identifiants invalides.',
    );
  });

  test('renvoie error.message si shape envelope', () {
    expect(
      extractDioError(_err({
        'error': {'message': 'OTP expiré', 'code': 'OTP_EXP'},
      })),
      'OTP expiré',
    );
  });

  test('renvoie premier champ DRF si erreurs par champ', () {
    expect(
      extractDioError(_err({
        'email': ['Adresse email invalide.'],
      })),
      'email : Adresse email invalide.',
    );
  });

  test('fallback sur e.message si data non parsable', () {
    final req = RequestOptions(path: '/x');
    final e = DioException(
      requestOptions: req,
      message: 'Connection refused',
    );
    expect(extractDioError(e), 'Connection refused');
  });

  test('non-DioException → toString', () {
    expect(extractDioError(StateError('bug')), contains('bug'));
  });
}
