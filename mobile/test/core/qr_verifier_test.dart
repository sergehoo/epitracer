import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mon_pass_sanitaire/core/api/api_client.dart';
import 'package:mon_pass_sanitaire/core/security/qr_verifier.dart';
import 'package:mon_pass_sanitaire/core/storage/local_cache.dart';
import 'package:path/path.dart' as p;

class _MockDio extends Mock implements Dio {}

class _FakeApi extends Fake implements ApiClient {
  _FakeApi(this.dio);
  @override
  final Dio dio;
}

void main() {
  setUpAll(() {
    registerFallbackValue(Options());
  });

  late Directory tmpDir;
  late LocalCache cache;
  late _MockDio dio;
  late ApiClient api;
  late SimpleKeyPair keyPair;
  late SimplePublicKey publicKey;
  late String pemPublicKey;

  setUp(() async {
    tmpDir = Directory.systemTemp.createTempSync('qr_test_');
    Hive.init(p.absolute(tmpDir.path));
    final c = await Hive.openBox<String>('cache');
    final m = await Hive.openBox<String>('meta');
    final d = await Hive.openBox<String>('drafts');
    cache = LocalCache(c, m, d);

    final ed25519 = Ed25519();
    keyPair = await ed25519.newKeyPair();
    publicKey = await keyPair.extractPublicKey();
    // PEM minimal — uniquement les 32 bytes encodés. Le parser tolère ce format.
    pemPublicKey = '-----BEGIN PUBLIC KEY-----\n'
        '${base64Encode(publicKey.bytes)}\n'
        '-----END PUBLIC KEY-----';

    dio = _MockDio();
    api = _FakeApi(dio);
  });

  tearDown(() async {
    await Hive.close();
    tmpDir.deleteSync(recursive: true);
  });

  Future<String> _buildSignedQr(Map<String, dynamic> payload) async {
    final ed = Ed25519();
    final sig = await ed.sign(
      utf8.encode(jsonEncode(payload)),
      keyPair: keyPair,
    );
    return jsonEncode({'payload': payload, 'sig': base64Encode(sig.bytes)});
  }

  test('QR valide → result.valid=true, expired=false', () async {
    when(() => dio.get(any(),
            options: any(named: 'options'),
            queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => Response(
              requestOptions: RequestOptions(path: '/passes/public-key.pem'),
              data: pemPublicKey,
              statusCode: 200,
            ));

    final verifier = QrVerifier(api, cache);
    final payload = {
      'pass_number': 'PASS-ABC',
      'full_name': 'KOUAME Yao',
      'disease': 'EBOLA',
      'exp': DateTime.now()
          .add(const Duration(days: 10))
          .toUtc()
          .toIso8601String(),
    };
    final qr = await _buildSignedQr(payload);

    final result = await verifier.verify(qr);
    expect(result.valid, isTrue);
    expect(result.expired, isFalse);
    expect(result.payload?['pass_number'], 'PASS-ABC');
  });

  test('QR expiré → result.expired=true, valid=false', () async {
    when(() => dio.get(any(),
            options: any(named: 'options'),
            queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => Response(
              requestOptions: RequestOptions(path: '/passes/public-key.pem'),
              data: pemPublicKey,
              statusCode: 200,
            ));

    final verifier = QrVerifier(api, cache);
    final payload = {
      'pass_number': 'PASS-OLD',
      'exp': DateTime.now()
          .subtract(const Duration(days: 5))
          .toUtc()
          .toIso8601String(),
    };
    final qr = await _buildSignedQr(payload);

    final result = await verifier.verify(qr);
    expect(result.expired, isTrue);
    expect(result.valid, isFalse);
    expect(result.reason, contains('expiré'));
  });

  test('Signature falsifiée → invalide', () async {
    when(() => dio.get(any(),
            options: any(named: 'options'),
            queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => Response(
              requestOptions: RequestOptions(path: '/passes/public-key.pem'),
              data: pemPublicKey,
              statusCode: 200,
            ));

    final verifier = QrVerifier(api, cache);
    final payload = {'pass_number': 'PASS-X'};
    final tampered = jsonEncode({
      'payload': payload,
      'sig': base64Encode(List<int>.filled(64, 0)), // signature factice
    });

    final result = await verifier.verify(tampered);
    expect(result.valid, isFalse);
    expect(result.reason, anyOf(contains('invalide'), contains('Signature')));
  });

  test('JSON malformé → reason explicite, pas de crash', () async {
    final verifier = QrVerifier(api, cache);
    final result = await verifier.verify('ceci nest pas du JSON');
    expect(result.valid, isFalse);
    expect(result.reason, contains('illisible'));
  });

  test('Clé publique mise en cache → 2e verify offline OK', () async {
    var callCount = 0;
    when(() => dio.get(any(),
            options: any(named: 'options'),
            queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async {
      callCount++;
      return Response(
        requestOptions: RequestOptions(path: '/passes/public-key.pem'),
        data: pemPublicKey,
        statusCode: 200,
      );
    });

    final verifier = QrVerifier(api, cache);
    final payload = {
      'pass_number': 'PASS-CACHED',
      'exp': DateTime.now()
          .add(const Duration(days: 1))
          .toUtc()
          .toIso8601String(),
    };
    final qr = await _buildSignedQr(payload);

    final r1 = await verifier.verify(qr);
    final r2 = await verifier.verify(qr);
    expect(r1.valid, isTrue);
    expect(r2.valid, isTrue);
    expect(callCount, 1, reason: 'la clé doit être réutilisée depuis le cache');
  });
}
