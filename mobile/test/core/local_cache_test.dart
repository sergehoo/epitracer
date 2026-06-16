import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mon_pass_sanitaire/core/storage/local_cache.dart';
import 'package:path/path.dart' as p;

void main() {
  late Directory tmpDir;
  late Box<String> cacheBox;
  late Box<String> metaBox;
  late Box<String> draftsBox;

  setUp(() async {
    tmpDir =
        Directory.systemTemp.createTempSync('hive_test_${DateTime.now().millisecondsSinceEpoch}');
    Hive.init(p.absolute(tmpDir.path));
    cacheBox = await Hive.openBox<String>('cache');
    metaBox = await Hive.openBox<String>('meta');
    draftsBox = await Hive.openBox<String>('drafts');
  });

  tearDown(() async {
    await Hive.close();
    tmpDir.deleteSync(recursive: true);
  });

  test('putJson + getJson round-trip Map', () async {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    await cache.putJson('profile', {'id': 42, 'email': 'a@b.ci'});
    final out = cache.getJson('profile');
    expect(out, isA<Map<String, dynamic>>());
    expect(out['email'], 'a@b.ci');
    expect(out['id'], 42);
  });

  test('putJson + getJson round-trip List', () async {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    await cache.putJson('passes', [
      {'id': 1, 'pass_number': 'PASS-AAA'},
      {'id': 2, 'pass_number': 'PASS-BBB'},
    ]);
    final out = cache.getJson('passes');
    expect(out, isA<List>());
    expect((out as List).length, 2);
    expect(out[0]['pass_number'], 'PASS-AAA');
  });

  test('getJson returns null when key absent', () {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    expect(cache.getJson('inexistant'), isNull);
  });

  test('timestamp is written and parseable', () async {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    final before = DateTime.now();
    await cache.putJson('foo', {'a': 1});
    final ts = cache.getJsonTimestamp('foo');
    expect(ts, isNotNull);
    expect(ts!.isAfter(before.subtract(const Duration(seconds: 1))), isTrue);
  });

  test('saveDraft + getDrafts + removeDraft', () async {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    await cache.saveDraft('checkin_1', {'fever': true});
    await cache.saveDraft('checkin_2', {'fever': false});

    final drafts = cache.getDrafts();
    expect(drafts.keys, containsAll(['checkin_1', 'checkin_2']));
    expect(drafts['checkin_1']['fever'], isTrue);

    await cache.removeDraft('checkin_1');
    expect(cache.getDrafts().keys, ['checkin_2']);
  });

  test('clearAll vide les 3 boxes', () async {
    final cache = LocalCache(cacheBox, metaBox, draftsBox);
    await cache.putJson('profile', {'id': 1});
    await cache.saveDraft('d1', {'x': 1});
    await cache.clearAll();
    expect(cache.getJson('profile'), isNull);
    expect(cache.getDrafts(), isEmpty);
  });
}
