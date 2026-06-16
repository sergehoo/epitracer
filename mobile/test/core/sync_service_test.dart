import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mon_pass_sanitaire/core/api/api_client.dart';
import 'package:mon_pass_sanitaire/core/storage/local_cache.dart';
import 'package:mon_pass_sanitaire/core/sync/sync_service.dart';
import 'package:path/path.dart' as p;

class _MockDio extends Mock implements Dio {}

class _FakeApi extends Fake implements ApiClient {
  _FakeApi(this.dio);
  @override
  final Dio dio;
}

void main() {
  setUpAll(() {
    registerFallbackValue(<String, dynamic>{});
  });

  late Directory tmpDir;
  late LocalCache cache;
  late _MockDio dio;

  setUp(() async {
    tmpDir = Directory.systemTemp.createTempSync('sync_test_');
    Hive.init(p.absolute(tmpDir.path));
    final c = await Hive.openBox<String>('cache');
    final m = await Hive.openBox<String>('meta');
    final d = await Hive.openBox<String>('drafts');
    cache = LocalCache(c, m, d);
    dio = _MockDio();
  });

  tearDown(() async {
    await Hive.close();
    tmpDir.deleteSync(recursive: true);
  });

  test('flushDrafts envoie chaque draft vers son endpoint et le supprime',
      () async {
    // Seed 3 drafts
    await cache.saveDraft('checkin_1', {'fever': false});
    await cache.saveDraft('vacc_draft_42', {'vaccine_name': 'Stamaril'});
    await cache.saveDraft('assist_99', {'message': 'help'});

    when(() => dio.post(any(), data: any(named: 'data'))).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/x'),
        statusCode: 201,
      ),
    );

    final container = ProviderContainer(overrides: [
      localCacheProvider.overrideWithValue(cache),
      apiClientProvider.overrideWithValue(_FakeApi(dio)),
    ]);
    addTearDown(container.dispose);

    final svc = container.read(syncServiceProvider);
    final sent = await svc.flushDrafts();

    expect(sent, 3);
    expect(cache.getDrafts(), isEmpty);

    verify(() => dio.post('/checkins/', data: any(named: 'data'))).called(1);
    verify(() => dio.post('/vaccinations/', data: any(named: 'data')))
        .called(1);
    verify(() => dio.post('/assistance/', data: any(named: 'data'))).called(1);
  });

  test('drafts au préfixe inconnu sont ignorés (conservés)', () async {
    await cache.saveDraft('random_garbage_1', {'x': 1});

    final container = ProviderContainer(overrides: [
      localCacheProvider.overrideWithValue(cache),
      apiClientProvider.overrideWithValue(_FakeApi(dio)),
    ]);
    addTearDown(container.dispose);

    final sent = await container.read(syncServiceProvider).flushDrafts();
    expect(sent, 0);
    expect(cache.getDrafts().keys, contains('random_garbage_1'));
    verifyNever(() => dio.post(any(), data: any(named: 'data')));
  });

  test('Échec serveur → draft conservé pour retry', () async {
    await cache.saveDraft('checkin_2', {'fever': true});

    when(() => dio.post('/checkins/', data: any(named: 'data')))
        .thenThrow(DioException(
      requestOptions: RequestOptions(path: '/checkins/'),
      type: DioExceptionType.connectionError,
    ));

    final container = ProviderContainer(overrides: [
      localCacheProvider.overrideWithValue(cache),
      apiClientProvider.overrideWithValue(_FakeApi(dio)),
    ]);
    addTearDown(container.dispose);

    final sent = await container.read(syncServiceProvider).flushDrafts();
    expect(sent, 0);
    expect(cache.getDrafts().keys, contains('checkin_2'));
  });
}
