import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mon_pass_sanitaire/core/api/api_client.dart';
import 'package:mon_pass_sanitaire/core/storage/local_cache.dart';
import 'package:mon_pass_sanitaire/features/passes/passes_repository.dart';
import 'package:path/path.dart' as p;

class _MockDio extends Mock implements Dio {}

class _FakeApi extends Fake implements ApiClient {
  _FakeApi(this.dio);
  @override
  final Dio dio;
}

void main() {
  late Directory tmpDir;
  late LocalCache cache;
  late _MockDio dio;
  late PassesRepository repo;

  final samplePass = {
    'id': 1,
    'pass_number': 'PASS-TEST-001',
    'disease': 'Ebola',
    'status': 'Actif',
    'issued_at': '2026-05-01T00:00:00Z',
    'expires_at': '2026-06-20T00:00:00Z',
  };

  setUp(() async {
    tmpDir = Directory.systemTemp.createTempSync('passes_repo_');
    Hive.init(p.absolute(tmpDir.path));
    final c = await Hive.openBox<String>('cache');
    final m = await Hive.openBox<String>('meta');
    final d = await Hive.openBox<String>('drafts');
    cache = LocalCache(c, m, d);
    dio = _MockDio();
    repo = PassesRepository(_FakeApi(dio), cache);
  });

  tearDown(() async {
    await Hive.close();
    tmpDir.deleteSync(recursive: true);
  });

  test('fetchPasses → API OK : remplit le cache', () async {
    when(() => dio.get('/passes/')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/passes/'),
        data: [samplePass],
        statusCode: 200,
      ),
    );

    final passes = await repo.fetchPasses();
    expect(passes, hasLength(1));
    expect(passes.first.passNumber, 'PASS-TEST-001');

    final cached = cache.getJson(CacheKeys.passes);
    expect(cached, isA<List>());
    expect((cached as List).length, 1);
  });

  test('fetchPasses → réseau KO : retombe sur cache', () async {
    await cache.putJson(CacheKeys.passes, [samplePass]);

    when(() => dio.get('/passes/')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/passes/'),
      type: DioExceptionType.connectionError,
    ));

    final passes = await repo.fetchPasses();
    expect(passes, hasLength(1));
    expect(passes.first.passNumber, 'PASS-TEST-001');
  });

  test('fetchPasses → cache vide + KO : liste vide, pas de crash', () async {
    when(() => dio.get('/passes/')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/passes/'),
      type: DioExceptionType.connectionError,
    ));

    final passes = await repo.fetchPasses();
    expect(passes, isEmpty);
  });

  test('fetchPasses gère le format {results: [...]} DRF', () async {
    when(() => dio.get('/passes/')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/passes/'),
        data: {
          'count': 1,
          'results': [samplePass],
        },
        statusCode: 200,
      ),
    );

    final passes = await repo.fetchPasses();
    expect(passes, hasLength(1));
    expect(passes.first.id, 1);
  });
}
