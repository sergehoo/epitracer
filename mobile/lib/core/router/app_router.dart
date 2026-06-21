import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/login_screen.dart';
import '../../features/auth/otp_screen.dart';
import '../../features/auth/voyageur_login_screen.dart';
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
import '../../features/followup/consent_screen.dart';
import '../../features/education/stories_screen.dart';
import '../../features/family/family_screen.dart';
import '../../features/map/map_screen.dart';
import '../../features/medical/medical_record_screen.dart';
import '../../features/registration/registration_picker_screen.dart';
import '../../features/registration/runner/form_runner_screen.dart';
import '../../features/registration/runner/form_success_screen.dart';
import '../../features/registration/runner/runner_models.dart';
import '../../features/settings/about_screen.dart';
import '../../features/settings/settings_screen.dart';
import '../../features/teleconsult/teleconsult_screen.dart';
import '../storage/secure_storage.dart';

class AppRoutes {
  static const splash = '/';
  static const onboarding = '/onboarding';
  static const voyageurLogin = '/voyageur-login';
  static const login = '/login';   // agent INHP (email + MFA)
  static const otp = '/otp';
  static const dashboard = '/dashboard';
  static const passes = '/passes';
  static const passDetail = '/passes/:id';
  static const qrFullscreen = '/passes/:id/qr';
  static const qrScanner = '/qr-scanner';
  static const vaccinations = '/vaccinations';
  static const followup = '/followup';
  static const checkin = '/followup/checkin';
  static const consent = '/followup/consent';
  static const notifications = '/notifications';
  static const assistance = '/assistance';
  static const profile = '/profile';
  static const medicalRecord = '/medical-record';
  static const map = '/map';
  static const stories = '/stories';
  static const family = '/family';
  static const teleconsult = '/teleconsultation';
  static const quizzes = '/quizzes';
  static const settings = '/settings';
  static const about = '/about';
  static const registration = '/registration';
  // Phase 8B — runner natif DynamicForm
  static const registrationRun = '/registration/run/:code';
  static const registrationSuccess = '/registration/success';
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
        AppRoutes.voyageurLogin,
        AppRoutes.login,
        AppRoutes.otp,
        AppRoutes.qrScanner,
        AppRoutes.registration,
      ];
      if (publicRoutes.contains(state.matchedLocation)) return null;
      // Phase 8B — le runner natif + l'écran succès sont publics.
      if (state.matchedLocation.startsWith('/registration/run/')) return null;
      if (state.matchedLocation == AppRoutes.registrationSuccess) return null;

      final hasSession = await storage.hasSession();
      // Redirection par défaut : voyageur (l'app cible le grand public)
      if (!hasSession) return AppRoutes.voyageurLogin;
      return null;
    },
    routes: [
      GoRoute(path: AppRoutes.splash, builder: (_, __) => const SplashScreen()),
      GoRoute(path: AppRoutes.onboarding, builder: (_, __) => const OnboardingScreen()),
      GoRoute(path: AppRoutes.voyageurLogin, builder: (_, __) => const VoyageurLoginScreen()),
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
      GoRoute(path: AppRoutes.consent, builder: (_, __) => const ConsentScreen()),
      GoRoute(path: AppRoutes.notifications, builder: (_, __) => const NotificationsScreen()),
      GoRoute(path: AppRoutes.assistance, builder: (_, __) => const AssistanceScreen()),
      GoRoute(path: AppRoutes.profile, builder: (_, __) => const ProfileScreen()),
      GoRoute(
        path: AppRoutes.medicalRecord,
        builder: (_, __) => const MedicalRecordScreen(),
      ),
      GoRoute(path: AppRoutes.map, builder: (_, __) => const MapScreen()),
      GoRoute(path: AppRoutes.family, builder: (_, __) => const FamilyScreen()),
      GoRoute(path: AppRoutes.stories, builder: (_, __) => const StoriesScreen()),
      GoRoute(path: AppRoutes.teleconsult, builder: (_, __) => const TeleconsultScreen()),
      GoRoute(path: AppRoutes.settings, builder: (_, __) => const SettingsScreen()),
      GoRoute(path: AppRoutes.about, builder: (_, __) => const AboutScreen()),
      GoRoute(
        path: AppRoutes.registration,
        builder: (_, __) => const RegistrationPickerScreen(),
      ),
      // Phase 8B — runner natif DynamicForm
      GoRoute(
        path: AppRoutes.registrationRun,
        builder: (_, state) {
          final code = state.pathParameters['code'] ?? '';
          return FormRunnerScreen(code: code);
        },
      ),
      GoRoute(
        path: AppRoutes.registrationSuccess,
        builder: (_, state) {
          final extra = state.extra;
          if (extra is SubmissionResult) {
            return FormSuccessScreen(result: extra);
          }
          // Pas de résultat → on retombe sur le picker, plutôt qu'un crash.
          return const RegistrationPickerScreen();
        },
      ),
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
