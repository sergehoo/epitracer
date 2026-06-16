import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mon_pass_sanitaire/core/api/api_client.dart';
import 'package:mon_pass_sanitaire/core/storage/local_cache.dart';
import 'package:mon_pass_sanitaire/features/vaccinations/vaccinations_repository.dart';
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
  late VaccinationsRepository repo;

  setUp(() async {
    tmpDir = Directory.systemTemp.createTempSync('vacc_repo_');
    Hive.init(p.absolute(tmpDir.path));
    final c = await Hive.openBox<String>('cache');
    final m = await Hive.openBox<String>('meta');
    final d = await Hive.openBox<String>('drafts');
    cache = LocalCache(c, m, d);
    dio = _MockDio();
    repo = VaccinationsRepository(_FakeApi(dio), cache);
  });

  tearDown(() async {
    await Hive.close();
    tmpDir.deleteSync(recursive: true);
  });

  test('create() KO réseau → sauvegarde un draft vacc_draft_*', () async {
    when(() => dio.post(any(), data: any(named: 'data'))).thenThrow(
      DioException(
        requestOptions: RequestOptions(path: '/vaccinations/'),
        type: DioExceptionType.connectionError,
      ),
    );

    final result = await repo.create({
      'disease_code': 'YF',
      'disease_name': 'Fièvre jaune',
      'vaccine_name': 'STAMARIL',
      'administered_at': '2026-03-15',
    });

    expect(result, isNull);
    final drafts = cache.getDrafts();
    expect(drafts.length, 1);
    expect(drafts.keys.first, startsWith('vacc_draft_'));
    expect(drafts.values.first['vaccine_name'], 'STAMARIL');
  });
}
