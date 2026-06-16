import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Service réactif de connectivité réseau.
/// Émet `true` (online) / `false` (offline) à chaque changement.
class ConnectivityService {
  ConnectivityService(this._connectivity) {
    _sub = _connectivity.onConnectivityChanged.listen((results) {
      _controller.add(_isOnline(results));
    });
    // État initial
    _connectivity.checkConnectivity().then((r) => _controller.add(_isOnline(r)));
  }

  final Connectivity _connectivity;
  final StreamController<bool> _controller = StreamController<bool>.broadcast();
  StreamSubscription<List<ConnectivityResult>>? _sub;

  Stream<bool> get onStatus => _controller.stream;

  Future<bool> isOnline() async {
    final r = await _connectivity.checkConnectivity();
    return _isOnline(r);
  }

  bool _isOnline(List<ConnectivityResult> results) {
    return results.any((r) =>
        r == ConnectivityResult.mobile ||
        r == ConnectivityResult.wifi ||
        r == ConnectivityResult.ethernet ||
        r == ConnectivityResult.vpn);
  }

  void dispose() {
    _sub?.cancel();
    _controller.close();
  }
}

final connectivityServiceProvider = Provider<ConnectivityService>((ref) {
  final svc = ConnectivityService(Connectivity());
  ref.onDispose(svc.dispose);
  return svc;
});

/// StreamProvider qui expose le statut en ligne en temps réel
final isOnlineProvider = StreamProvider<bool>((ref) {
  return ref.watch(connectivityServiceProvider).onStatus;
});
