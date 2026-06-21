/// State du runner DynamicForm (Phase 8B).
///
/// Un ChangeNotifier qui :
///   - garde la map `answers` { fieldCode → value }
///   - garde les `errors` par fieldCode pour l'affichage inline
///   - expose `validateSection(idx)` qui retourne true/false
///   - sauve un brouillon Hive toutes les 10s (auto-save)
///   - expose `submit()` qui appelle le repository et retourne SubmissionResult
library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'runner_models.dart';
import 'runner_repository.dart';

class FormRunnerState extends ChangeNotifier {
  FormRunnerState({
    required this.schema,
    required FormRunnerRepository repository,
  }) : _repo = repository {
    // Charge brouillon existant si présent.
    _loadDraft();
    // Auto-save toutes les 10s — économe en I/O, suffisant en pratique.
    _autoSaveTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (_dirty) _saveDraft();
    });
  }

  final FormSchema schema;
  final FormRunnerRepository _repo;
  Timer? _autoSaveTimer;

  final Map<String, dynamic> _answers = {};
  final Map<String, String> _errors = {};
  int _currentSection = 0;
  bool _dirty = false;
  bool _submitting = false;
  String? _submissionError;

  Map<String, dynamic> get answers => Map.unmodifiable(_answers);
  Map<String, String> get errors => Map.unmodifiable(_errors);
  int get currentSection => _currentSection;
  bool get submitting => _submitting;
  String? get submissionError => _submissionError;

  int get totalSections => schema.sections.length;
  double get progress =>
      totalSections == 0 ? 0 : (_currentSection + 1) / totalSections;
  bool get isLastSection => _currentSection == totalSections - 1;
  bool get isFirstSection => _currentSection == 0;

  FormSectionSchema? get currentSectionSchema =>
      _currentSection < schema.sections.length
          ? schema.sections[_currentSection]
          : null;

  void _loadDraft() {
    final draft = _repo.loadDraft(schema.code);
    if (draft != null) {
      final a = draft['answers'];
      if (a is Map) {
        _answers.addAll(Map<String, dynamic>.from(a));
      }
      final si = draft['section_index'];
      if (si is int && si >= 0 && si < totalSections) {
        _currentSection = si;
      }
    }
  }

  Future<void> _saveDraft() async {
    _dirty = false;
    await _repo.saveDraft(schema.code, _answers, sectionIndex: _currentSection);
  }

  /// Sauvegarde manuelle (déclenchée par "Sauvegarder & quitter").
  Future<void> saveDraftNow() async {
    await _saveDraft();
  }

  void setAnswer(String fieldCode, dynamic value) {
    if (value == null || (value is String && value.isEmpty)) {
      _answers.remove(fieldCode);
    } else {
      _answers[fieldCode] = value;
    }
    _errors.remove(fieldCode);
    _dirty = true;
    notifyListeners();
  }

  /// Le champ doit-il être visible compte tenu de ses conditions ?
  ///
  /// Implémentation simple pour Phase 8B :
  ///   - `show` : visible SEULEMENT si toutes les conditions sont vraies
  ///   - `hide` : caché si toutes les conditions sont vraies
  ///   - `require` : ne change pas la visibilité, juste la requireness
  ///
  /// On résout `depends_on` (id de FormField) en parcourant le schema.
  bool isFieldVisible(FormFieldSchema field) {
    if (field.conditions.isEmpty) return true;
    bool? forcedShow;
    for (final cond in field.conditions) {
      if (cond.action == 'require') continue; // gérée par isFieldRequired
      final depField = _findFieldById(cond.dependsOn);
      if (depField == null) continue;
      final depValue = _answers[depField.code];
      final ok = _evaluate(depValue, cond.operator, cond.expectedValue);
      if (cond.action == 'show') {
        forcedShow = (forcedShow ?? true) && ok;
      } else if (cond.action == 'hide') {
        if (ok) return false;
      }
    }
    return forcedShow ?? true;
  }

  /// Le champ est-il requis (statique OU rendu requis par une condition) ?
  bool isFieldRequired(FormFieldSchema field) {
    if (field.isRequired) return true;
    for (final cond in field.conditions) {
      if (cond.action != 'require') continue;
      final depField = _findFieldById(cond.dependsOn);
      if (depField == null) continue;
      final depValue = _answers[depField.code];
      if (_evaluate(depValue, cond.operator, cond.expectedValue)) return true;
    }
    return false;
  }

  FormFieldSchema? _findFieldById(int id) {
    for (final section in schema.sections) {
      for (final f in section.fields) {
        if (f.id == id) return f;
      }
    }
    return null;
  }

  bool _evaluate(dynamic actual, String op, String expected) {
    final a = (actual ?? '').toString();
    switch (op) {
      case 'eq':
        return a == expected;
      case 'ne':
        return a != expected;
      case 'gt':
        final na = double.tryParse(a);
        final ne = double.tryParse(expected);
        return (na != null && ne != null) && na > ne;
      case 'lt':
        final na = double.tryParse(a);
        final ne = double.tryParse(expected);
        return (na != null && ne != null) && na < ne;
      case 'contains':
        return a.contains(expected);
      case 'in':
        return expected.split(',').map((s) => s.trim()).contains(a);
      default:
        return false;
    }
  }

  /// Valide tous les champs de la section [index]. Retourne true si OK.
  /// Met à jour _errors et notifie les listeners.
  bool validateSection(int index) {
    if (index < 0 || index >= totalSections) return true;
    final section = schema.sections[index];
    _errors.removeWhere((code, _) =>
        section.fields.any((f) => f.code == code));
    bool ok = true;
    for (final field in section.fields) {
      if (!isFieldVisible(field)) continue;
      final err = _validateField(field);
      if (err != null) {
        _errors[field.code] = err;
        ok = false;
      }
    }
    notifyListeners();
    return ok;
  }

  String? _validateField(FormFieldSchema f) {
    final v = _answers[f.code];
    final required = isFieldRequired(f);

    bool isEmpty(dynamic x) {
      if (x == null) return true;
      if (x is String) return x.trim().isEmpty;
      if (x is List) return x.isEmpty;
      return false;
    }

    if (required && isEmpty(v)) {
      return 'Ce champ est obligatoire.';
    }
    if (isEmpty(v)) return null;

    switch (f.kind) {
      case FieldKind.email:
        final s = v.toString();
        if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(s)) {
          return 'Adresse e-mail invalide.';
        }
        break;
      case FieldKind.phone:
        final s = v.toString().replaceAll(RegExp(r'[\s\-\.]'), '');
        if (!RegExp(r'^\+?\d{6,15}$').hasMatch(s)) {
          return 'Numéro de téléphone invalide.';
        }
        break;
      case FieldKind.number:
      case FieldKind.integer:
        final n = double.tryParse(v.toString());
        if (n == null) return 'Valeur numérique attendue.';
        if (f.minValue != null && n < f.minValue!) {
          return 'Valeur minimale : ${f.minValue}.';
        }
        if (f.maxValue != null && n > f.maxValue!) {
          return 'Valeur maximale : ${f.maxValue}.';
        }
        if (f.kind == FieldKind.integer && n != n.truncateToDouble()) {
          return 'Valeur entière attendue.';
        }
        break;
      case FieldKind.text:
      case FieldKind.textarea:
        final s = v.toString();
        if (f.minLength != null && s.length < f.minLength!) {
          return 'Minimum ${f.minLength} caractères.';
        }
        if (f.maxLength != null && s.length > f.maxLength!) {
          return 'Maximum ${f.maxLength} caractères.';
        }
        if (f.regex.isNotEmpty) {
          try {
            if (!RegExp(f.regex).hasMatch(s)) {
              return 'Format invalide.';
            }
          } catch (_) {/* regex invalide côté backend — on skip */}
        }
        break;
      default:
        break;
    }
    return null;
  }

  bool goNext() {
    if (!validateSection(_currentSection)) return false;
    if (isLastSection) return false;
    _currentSection++;
    _dirty = true;
    notifyListeners();
    return true;
  }

  void goPrevious() {
    if (_currentSection > 0) {
      _currentSection--;
      _dirty = true;
      notifyListeners();
    }
  }

  /// Soumet le formulaire complet. Valide TOUTES les sections avant envoi.
  /// Retourne SubmissionResult en cas de succès, sinon throw.
  Future<SubmissionResult> submit() async {
    // Validation globale : on parcourt toutes les sections pour collecter
    // les erreurs et bloquer si la moindre est invalide.
    bool allOk = true;
    for (var i = 0; i < totalSections; i++) {
      if (!validateSection(i)) {
        allOk = false;
        // On positionne le user sur la première section avec une erreur.
        if (_currentSection > i) _currentSection = i;
      }
    }
    if (!allOk) {
      notifyListeners();
      throw const FormatException(
          'Veuillez compléter les champs obligatoires avant de soumettre.');
    }

    _submitting = true;
    _submissionError = null;
    notifyListeners();
    try {
      // La signature peut être stockée dans answers sous une clé spéciale.
      final signature = _answers['__signature_data_url'] as String?;
      // On exclut les clés internes du payload.
      final payloadAnswers = Map<String, dynamic>.from(_answers)
        ..remove('__signature_data_url');
      final result = await _repo.submit(
        schema.code,
        answers: payloadAnswers,
        signatureDataUrl: signature,
      );
      _submitting = false;
      notifyListeners();
      return result;
    } catch (e) {
      _submitting = false;
      _submissionError = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  @override
  void dispose() {
    _autoSaveTimer?.cancel();
    // Sauve une dernière fois avant disposal (sans await dans dispose).
    if (_dirty) {
      // Best-effort : fire-and-forget.
      _repo.saveDraft(schema.code, _answers, sectionIndex: _currentSection);
    }
    super.dispose();
  }
}
