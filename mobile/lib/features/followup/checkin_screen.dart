import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';

import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_colors.dart';
import 'followup_repository.dart';

/// Écran de check-in quotidien — parité PWA /voyageur/suivi.
///
/// Reproduit le parcours de la PWA :
///   1. 3 boutons rapides : "Je vais bien" / "Symptôme" / "Assistance"
///   2. Formulaire détaillé si symptôme : toggles symptômes + intensité,
///      température, notes.
///   3. Si symptôme critique sélectionné → bandeau rouge persistant.
///   4. Si géoloc consentie → tentative best-effort de captation position.
class CheckinScreen extends ConsumerStatefulWidget {
  const CheckinScreen({super.key});

  @override
  ConsumerState<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends ConsumerState<CheckinScreen> {
  bool _showSymptomForm = false;
  bool _submitting = false;

  final Map<String, bool> _symptoms = {};
  final Map<String, SymptomSeverity> _severities = {};
  final _temperatureCtl = TextEditingController();
  final _notesCtl = TextEditingController();

  @override
  void dispose() {
    _temperatureCtl.dispose();
    _notesCtl.dispose();
    super.dispose();
  }

  bool get _hasCriticalSelected {
    for (final s in kSymptoms) {
      if (s.critical && _symptoms[s.key] == true) return true;
    }
    return false;
  }

  bool get _anySelected => _symptoms.values.any((v) => v);

  Future<({double? lat, double? lng, double? acc})> _tryGetPosition({
    required bool consented,
  }) async {
    if (!consented) return (lat: null, lng: null, acc: null);
    try {
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) return (lat: null, lng: null, acc: null);
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm != LocationPermission.always &&
          perm != LocationPermission.whileInUse) {
        return (lat: null, lng: null, acc: null);
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 12),
        ),
      );
      return (lat: pos.latitude, lng: pos.longitude, acc: pos.accuracy);
    } catch (_) {
      return (lat: null, lng: null, acc: null);
    }
  }

  Future<void> _send(String feeling) async {
    final publicId =
        await ref.read(secureStorageProvider).getPublicId() ?? '';
    if (publicId.isEmpty) {
      _showError(
        "Identifiant voyageur introuvable. "
        "Reconnectez-vous depuis l'écran d'accueil.",
      );
      return;
    }
    setState(() => _submitting = true);

    // On consulte le statut pour savoir si le consentement géoloc est actif.
    // En cas d'échec (offline), on ne tente pas la géoloc — c'est le
    // comportement le plus prudent côté privacy.
    final status =
        await ref.read(followupRepositoryProvider).fetchFollowUpStatus();
    final pos = await _tryGetPosition(
      consented: status?.geolocationConsented == true,
    );

    final temp = double.tryParse(_temperatureCtl.text.replaceAll(',', '.'));

    final payload = CheckinSubmission(
      publicId: publicId,
      feeling: feeling,
      symptoms: Map.unmodifiable(_symptoms),
      symptomSeverities: Map.unmodifiable(_severities),
      temperatureCelsius: temp,
      notes: _notesCtl.text.trim(),
      needsContact: feeling == 'assistance',
      latitude: pos.lat,
      longitude: pos.lng,
      accuracyM: pos.acc,
    );

    final result =
        await ref.read(followupRepositoryProvider).submitPublicCheckin(payload);

    // Force rafraîchissement du statut suivi pour le compteur jour + last_check
    ref.invalidate(followUpStatusProvider);
    ref.invalidate(followupSummaryProvider);

    if (!mounted) return;
    setState(() => _submitting = false);

    await showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        icon: Icon(
          result.ok
              ? Icons.check_circle
              : (result.offlineDraft ? Icons.cloud_off : Icons.error_outline),
          color: result.ok
              ? AppColors.statusOk
              : (result.offlineDraft
                  ? AppColors.statusWarn
                  : AppColors.statusDanger),
          size: 48,
        ),
        title: Text(result.ok
            ? 'Merci pour votre confirmation'
            : (result.offlineDraft
                ? 'Enregistré hors-ligne'
                : 'Erreur')),
        content: Text(result.message, textAlign: TextAlign.center),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              context.pop();
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.statusDanger),
    );
  }

  Future<void> _callEmergency() async {
    // Numéro Allô Santé. Le bouton appel est dans le bandeau critique.
    HapticFeedback.mediumImpact();
    await Clipboard.setData(const ClipboardData(text: '143'));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Numéro 143 copié — composez-le depuis votre téléphone.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Check-in du jour')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            "Comment vous sentez-vous aujourd'hui ?",
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text(
            "Vos réponses restent confidentielles et nous permettent de mieux vous accompagner.",
            style: TextStyle(color: AppColors.slate500),
          ),
          const SizedBox(height: 24),

          // Bandeau critique persistant si un symptôme critique est coché
          if (_showSymptomForm && _hasCriticalSelected) ...[
            _CriticalBanner(onCallTap: _callEmergency),
            const SizedBox(height: 16),
          ],

          // 1) Mode boutons rapides
          if (!_showSymptomForm) ...[
            _QuickChoice(
              icon: Icons.sentiment_satisfied,
              color: AppColors.statusOk,
              title: 'Je vais bien',
              subtitle: 'Confirmer mon état du jour',
              onTap: _submitting ? null : () => _send('ok'),
            ),
            const SizedBox(height: 10),
            _QuickChoice(
              icon: Icons.thermostat,
              color: AppColors.statusWarn,
              title: 'Je ressens un symptôme',
              subtitle: 'Décrire calmement ce que je ressens',
              onTap: _submitting
                  ? null
                  : () => setState(() => _showSymptomForm = true),
            ),
            const SizedBox(height: 10),
            _QuickChoice(
              icon: Icons.health_and_safety,
              color: AppColors.statusDanger,
              title: "J'ai besoin d'aide",
              subtitle: 'Une équipe me recontactera',
              onTap: _submitting ? null : () => _send('assistance'),
            ),
          ],

          // 2) Mode formulaire symptômes
          if (_showSymptomForm) ...[
            const Text(
              'Précisez ce que vous ressentez',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
            const SizedBox(height: 4),
            const Text(
              "Aucune réponse n'est obligatoire. Indiquez seulement ce qui vous concerne.",
              style: TextStyle(color: AppColors.slate500, fontSize: 12.5),
            ),
            const SizedBox(height: 16),
            for (final s in kSymptoms)
              _SymptomTile(
                symptom: s,
                selected: _symptoms[s.key] == true,
                severity: _severities[s.key],
                onToggle: (v) {
                  setState(() {
                    _symptoms[s.key] = v;
                    if (!v) _severities.remove(s.key);
                    if (v && _severities[s.key] == null) {
                      _severities[s.key] = SymptomSeverity.mild;
                    }
                  });
                },
                onSeverity: (sev) {
                  setState(() => _severities[s.key] = sev);
                },
              ),
            const SizedBox(height: 12),
            const Text(
              'Température (°C)',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _temperatureCtl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]')),
                LengthLimitingTextInputFormatter(5),
              ],
              decoration: const InputDecoration(
                hintText: 'Ex : 37.2',
                suffixText: '°C',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Notes (optionnel)',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _notesCtl,
              maxLines: 3,
              maxLength: 500,
              decoration: const InputDecoration(
                hintText: 'Sommeil, appétit, contexte…',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                TextButton(
                  onPressed: _submitting
                      ? null
                      : () => setState(() => _showSymptomForm = false),
                  child: const Text('Annuler'),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: _submitting || !_anySelected
                      ? null
                      : () => _send('symptom'),
                  icon: const Icon(Icons.send),
                  label: Text(_submitting ? 'Envoi…' : 'Envoyer'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// ============================================================================
/// Widgets internes
/// ============================================================================

class _QuickChoice extends StatelessWidget {
  const _QuickChoice({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withValues(alpha: 0.3)),
            color: color.withValues(alpha: 0.06),
          ),
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        color: color,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: AppColors.slate500,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: color),
            ],
          ),
        ),
      ),
    );
  }
}

class _SymptomTile extends StatelessWidget {
  const _SymptomTile({
    required this.symptom,
    required this.selected,
    required this.onToggle,
    required this.onSeverity,
    this.severity,
  });

  final SymptomDef symptom;
  final bool selected;
  final SymptomSeverity? severity;
  final ValueChanged<bool> onToggle;
  final ValueChanged<SymptomSeverity> onSeverity;

  @override
  Widget build(BuildContext context) {
    final accent =
        symptom.critical ? AppColors.statusDanger : AppColors.statusWarn;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: selected
              ? accent.withValues(alpha: 0.4)
              : Colors.transparent,
          width: 1.2,
        ),
      ),
      child: Column(
        children: [
          SwitchListTile.adaptive(
            value: selected,
            onChanged: onToggle,
            activeColor: accent,
            title: Row(
              children: [
                Expanded(
                  child: Text(
                    symptom.label,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                if (symptom.critical) ...[
                  const SizedBox(width: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.statusDanger.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'À surveiller',
                      style: TextStyle(
                        color: AppColors.statusDanger,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (selected)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Row(
                children: [
                  const Text(
                    'Intensité :',
                    style: TextStyle(
                      color: AppColors.slate500,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SegmentedButton<SymptomSeverity>(
                      segments: const [
                        ButtonSegment(
                          value: SymptomSeverity.mild,
                          label: Text('Légère',
                              style: TextStyle(fontSize: 11)),
                        ),
                        ButtonSegment(
                          value: SymptomSeverity.moderate,
                          label: Text('Modérée',
                              style: TextStyle(fontSize: 11)),
                        ),
                        ButtonSegment(
                          value: SymptomSeverity.severe,
                          label: Text('Sévère',
                              style: TextStyle(fontSize: 11)),
                        ),
                      ],
                      selected: {severity ?? SymptomSeverity.mild},
                      onSelectionChanged: (set) {
                        if (set.isNotEmpty) onSeverity(set.first);
                      },
                      showSelectedIcon: false,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _CriticalBanner extends StatelessWidget {
  const _CriticalBanner({required this.onCallTap});
  final VoidCallback onCallTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.statusDanger, Color(0xFFB91C1C)],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AppColors.statusDanger.withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.warning_amber_rounded,
                color: Colors.white, size: 26),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Symptôme à surveiller',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Contactez immédiatement le 143 (Allô Santé).',
                  style: TextStyle(color: Colors.white, fontSize: 12.5),
                ),
              ],
            ),
          ),
          ElevatedButton.icon(
            onPressed: onCallTap,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: AppColors.statusDanger,
              padding: const EdgeInsets.symmetric(horizontal: 10),
            ),
            icon: const Icon(Icons.call),
            label: const Text('143',
                style: TextStyle(fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }
}
