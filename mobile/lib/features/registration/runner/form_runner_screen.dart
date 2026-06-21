/// Écran principal du DynamicForm runner (Phase 8B).
/// Reçoit `code` en path-param → fetch schema → rend section par section.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/app_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_gradients.dart';
import 'field_renderer.dart';
import 'form_runner_state.dart';
import 'runner_models.dart';
import 'runner_repository.dart';

class FormRunnerScreen extends ConsumerWidget {
  const FormRunnerScreen({super.key, required this.code});

  final String code;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(formSchemaProvider(code));
    return async.when(
      loading: () => Scaffold(
        appBar: AppBar(
          title: const Text('Chargement du formulaire'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go(AppRoutes.registration),
          ),
        ),
        body: const Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(
          title: const Text('Formulaire indisponible'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go(AppRoutes.registration),
          ),
        ),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off,
                  color: AppColors.slate300, size: 64),
              const SizedBox(height: 12),
              const Text(
                'Connexion impossible',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              const Text(
                'Vérifiez votre connexion internet et réessayez.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.slate500),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: () => ref.invalidate(formSchemaProvider(code)),
                icon: const Icon(Icons.refresh),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      ),
      data: (schema) => _FormRunnerBody(schema: schema),
    );
  }
}

class _FormRunnerBody extends ConsumerStatefulWidget {
  const _FormRunnerBody({required this.schema});
  final FormSchema schema;

  @override
  ConsumerState<_FormRunnerBody> createState() => _FormRunnerBodyState();
}

class _FormRunnerBodyState extends ConsumerState<_FormRunnerBody> {
  late final FormRunnerState _state;

  @override
  void initState() {
    super.initState();
    _state = FormRunnerState(
      schema: widget.schema,
      repository: ref.read(formRunnerRepositoryProvider),
    );
    _state.addListener(_onStateChanged);
  }

  void _onStateChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _state.removeListener(_onStateChanged);
    _state.dispose();
    super.dispose();
  }

  Future<void> _saveAndQuit() async {
    await _state.saveDraftNow();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Brouillon sauvegardé.')),
    );
    if (mounted) context.go(AppRoutes.registration);
  }

  Future<void> _onPrimaryPressed() async {
    if (!_state.isLastSection) {
      final advanced = _state.goNext();
      if (!advanced && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Veuillez corriger les erreurs avant de continuer.'),
            backgroundColor: AppColors.statusDanger,
          ),
        );
      }
      return;
    }
    // Dernière section → submit
    try {
      final result = await _state.submit();
      if (!mounted) return;
      context.go('${AppRoutes.registration}/success', extra: result);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Soumission impossible : ${_safeError(e)}'),
          backgroundColor: AppColors.statusDanger,
          duration: const Duration(seconds: 5),
        ),
      );
    }
  }

  /// Évite d'afficher du PII / des tokens dans les snackbars d'erreur.
  String _safeError(Object e) {
    final s = e.toString();
    if (s.length > 140) return '${s.substring(0, 140)}…';
    return s;
  }

  @override
  Widget build(BuildContext context) {
    final section = _state.currentSectionSchema;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.schema.title,
          style: const TextStyle(fontSize: 15),
          overflow: TextOverflow.ellipsis,
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(AppRoutes.registration),
        ),
        actions: [
          TextButton.icon(
            onPressed: _saveAndQuit,
            icon: const Icon(Icons.save_outlined,
                size: 16, color: AppColors.ciDark),
            label: const Text(
              'Sauvegarder',
              style: TextStyle(color: AppColors.ciDark),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(6),
          child: LinearProgressIndicator(
            value: _state.progress,
            minHeight: 4,
            backgroundColor: AppColors.slate100,
            valueColor: const AlwaysStoppedAnimation(AppColors.ciGreen),
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.neutralLight),
        child: SafeArea(
          child: section == null
              ? const Center(child: Text('Formulaire vide.'))
              : Column(
                  children: [
                    // Indicateur de section X/N
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: AppColors.ciGreen,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              'Section ${_state.currentSection + 1}/${_state.totalSections}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              section.title,
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: AppColors.ciDark,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (section.description.isNotEmpty)
                      Padding(
                        padding:
                            const EdgeInsets.fromLTRB(20, 4, 20, 0),
                        child: Text(
                          section.description,
                          style: const TextStyle(
                            color: AppColors.slate500,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
                        children: [
                          for (final field in section.fields)
                            if (_state.isFieldVisible(field))
                              FieldRenderer(
                                field: field,
                                value: _state.answers[field.code],
                                error: _state.errors[field.code],
                                required: _state.isFieldRequired(field),
                                onChanged: (v) =>
                                    _state.setAnswer(field.code, v),
                              ),
                        ],
                      ),
                    ),
                    _BottomBar(
                      state: _state,
                      onPrev: _state.isFirstSection
                          ? null
                          : _state.goPrevious,
                      onNext: _state.submitting ? null : _onPrimaryPressed,
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.state,
    required this.onPrev,
    required this.onNext,
  });
  final FormRunnerState state;
  final VoidCallback? onPrev;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Row(
        children: [
          if (onPrev != null) ...[
            Expanded(
              child: OutlinedButton.icon(
                onPressed: onPrev,
                icon: const Icon(Icons.arrow_back, size: 16),
                label: const Text('Précédent'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  foregroundColor: AppColors.slate700,
                  side: const BorderSide(color: AppColors.slate200),
                ),
              ),
            ),
            const SizedBox(width: 10),
          ],
          Expanded(
            flex: 2,
            child: ElevatedButton.icon(
              onPressed: onNext,
              icon: state.submitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2),
                    )
                  : Icon(
                      state.isLastSection
                          ? Icons.check_circle_outline
                          : Icons.arrow_forward,
                      size: 18,
                    ),
              label: Text(
                state.submitting
                    ? 'Envoi…'
                    : (state.isLastSection ? 'Soumettre' : 'Suivant'),
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                backgroundColor: AppColors.ciGreen,
                foregroundColor: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
