import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mon_pass_sanitaire/core/network/connectivity_service.dart';
import 'package:mon_pass_sanitaire/shared/widgets/offline_banner.dart';

void main() {
  testWidgets('OfflineBanner caché quand online', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          isOnlineProvider.overrideWith(
            (ref) => Stream<bool>.value(true),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: OfflineBanner()),
        ),
      ),
    );
    await tester.pump();
    expect(find.byIcon(Icons.wifi_off), findsNothing);
    expect(find.textContaining('Mode hors-ligne'), findsNothing);
  });

  testWidgets('OfflineBanner visible quand offline', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          isOnlineProvider.overrideWith(
            (ref) => Stream<bool>.value(false),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: OfflineBanner()),
        ),
      ),
    );
    await tester.pump();
    expect(find.byIcon(Icons.wifi_off), findsOneWidget);
    expect(find.textContaining('Mode hors-ligne'), findsOneWidget);
  });

  testWidgets('WithOfflineBanner enveloppe child correctement', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          isOnlineProvider.overrideWith(
            (ref) => Stream<bool>.value(true),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: WithOfflineBanner(
              child: Center(child: Text('CONTENT')),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('CONTENT'), findsOneWidget);
  });
}
