import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/login_screen.dart';
import '../../features/auth/otp_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../../features/onboarding/onboarding_screen.dart';
import '../../features/onboarding/splash_screen.dart';
import '../../features/passes/pass_detail_screen.dart';
import '../../features/passes/passes_list_screen.dart';
import '../../features/passes/qr_fullscreen.dart';
import '../../features/qr_scanner/qr_scanner_screen.dart';
import '../../features/assistance/assistance_screen.dart';
import '../../features/notifications/notifications_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/vaccinations/vaccinations_screen.dart';
import '../../features/followup/followup_screen.dart';
import '../../features/followup/checkin_screen.dart';
import '../storage/secure_storage.dart';

class AppRoutes {
  static const splash = '/';
  static const onboarding = '/onboarding';
  static const login = '/login';
  static const otp = '/otp';
  static const dashboard = '/dashboard';
  static const passes = '/passes';
  static const passDetail = '/passes/:id';
  static const qrFullscreen = '/passes/:id/qr';
  static const qrScanner = '/qr-scanner';
  static const vaccinations = '/vaccinations';
  static const followup = '/followup';
  static const checkin = '/followup/checkin';
  static const notifications = '/notifications';
  static const assistance = '/assistance';
  static const profile = '/profile';
}

final routerProvider = Provider<GoRouter>((ref) {
  final storage = ref.watch(secureStorageProvider);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: false,
    redirect: (context, state) async {
      // Routes publiques (pas besoin d'auth)
      final publicRoutes = [
        AppRoutes.splash,
        AppRoutes.onboarding,
        AppRoutes.login,
        AppRoutes.otp,
        AppRoutes.qrScanner,
      ];
      if (publicRoutes.contains(state.matchedLocation)) return null;

      final hasSession = await storage.hasSession();
      if (!hasSession) return AppRoutes.login;
      return null;
    },
    routes: [
      GoRoute(path: AppRoutes.splash, builder: (_, __) => const SplashScreen()),
      GoRoute(path: AppRoutes.onboarding, builder: (_, __) => const OnboardingScreen()),
      GoRoute(path: AppRoutes.login, builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: AppRoutes.otp,
        builder: (_, state) {
          final email = state.uri.queryParameters['email'] ?? '';
          return OtpScreen(email: email);
        },
      ),
      GoRoute(path: AppRoutes.dashboard, builder: (_, __) => const DashboardScreen()),
      GoRoute(path: AppRoutes.passes, builder: (_, __) => const PassesListScreen()),
      GoRoute(
        path: AppRoutes.passDetail,
        builder: (_, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return PassDetailScreen(passId: id);
        },
      ),
      GoRoute(
        path: AppRoutes.qrFullscreen,
        builder: (_, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return QrFullscreenScreen(passId: id);
        },
      ),
      GoRoute(path: AppRoutes.qrScanner, builder: (_, __) => const QrScannerScreen()),
      GoRoute(path: AppRoutes.vaccinations, builder: (_, __) => const VaccinationsScreen()),
      GoRoute(path: AppRoutes.followup, builder: (_, __) => const FollowupScreen()),
      GoRoute(path: AppRoutes.checkin, builder: (_, __) => const CheckinScreen()),
      GoRoute(path: AppRoutes.notifications, builder: (_, __) => const NotificationsScreen()),
      GoRoute(path: AppRoutes.assistance, builder: (_, __) => const AssistanceScreen()),
      GoRoute(path: AppRoutes.profile, builder: (_, __) => const ProfileScreen()),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            'Page introuvable\n${state.uri.path}',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    ),
  );
});
