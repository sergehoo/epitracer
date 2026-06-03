import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';

class CheckinScreen extends StatefulWidget {
  const CheckinScreen({super.key});

  @override
  State<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends State<CheckinScreen> {
  bool feelingWell = true;
  bool fever = false;
  bool fatigue = false;
  bool headache = false;
  bool muscle = false;
  bool digestive = false;
  bool bleeding = false;
  bool wantsContact = false;

  bool _submitting = false;

  Future<void> _submit() async {
    setState(() => _submitting = true);
    // TODO Phase 2 — POST /mobile/checkins/
    await Future<void>.delayed(const Duration(seconds: 1));
    if (!mounted) return;
    setState(() => _submitting = false);

    await showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        icon: const Icon(Icons.check_circle,
            color: AppColors.statusOk, size: 48),
        title: const Text('Merci pour votre confirmation'),
        content: const Text(
          'Votre suivi est bien enregistré. Les équipes sanitaires restent disponibles si vous avez besoin d\'aide.',
          textAlign: TextAlign.center,
        ),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Check-in du jour')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Comment vous sentez-vous aujourd\'hui ?',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text(
            'Vos réponses sont confidentielles et aident l\'INHP à mieux vous accompagner.',
            style: TextStyle(color: AppColors.slate500),
          ),
          const SizedBox(height: 24),

          _Choice(
            label: 'Je vais bien',
            icon: Icons.sentiment_satisfied,
            color: AppColors.statusOk,
            value: feelingWell,
            onChanged: (v) => setState(() => feelingWell = v),
          ),
          const SizedBox(height: 8),
          _Choice(
            label: 'J\'ai de la fièvre',
            icon: Icons.thermostat,
            color: AppColors.statusDanger,
            value: fever,
            onChanged: (v) => setState(() {
              fever = v;
              if (v) feelingWell = false;
            }),
          ),
          _Choice(
            label: 'J\'ai une fatigue inhabituelle',
            icon: Icons.battery_alert,
            color: AppColors.statusWarn,
            value: fatigue,
            onChanged: (v) => setState(() => fatigue = v),
          ),
          _Choice(
            label: 'J\'ai des maux de tête',
            icon: Icons.psychology,
            color: AppColors.statusWarn,
            value: headache,
            onChanged: (v) => setState(() => headache = v),
          ),
          _Choice(
            label: 'J\'ai des douleurs musculaires',
            icon: Icons.accessibility_new,
            color: AppColors.statusWarn,
            value: muscle,
            onChanged: (v) => setState(() => muscle = v),
          ),
          _Choice(
            label: 'J\'ai des vomissements ou diarrhée',
            icon: Icons.sick,
            color: AppColors.statusDanger,
            value: digestive,
            onChanged: (v) => setState(() => digestive = v),
          ),
          _Choice(
            label: 'J\'ai des saignements inexpliqués',
            icon: Icons.bloodtype,
            color: AppColors.statusDanger,
            value: bleeding,
            onChanged: (v) => setState(() => bleeding = v),
          ),
          const SizedBox(height: 16),
          _Choice(
            label: 'Je souhaite être contacté par les équipes sanitaires',
            icon: Icons.phone_in_talk,
            color: AppColors.statusInfo,
            value: wantsContact,
            onChanged: (v) => setState(() => wantsContact = v),
          ),
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: _submitting ? null : _submit,
            child: _submitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Text('Envoyer mon check-in'),
          ),
        ],
      ),
    );
  }
}

class _Choice extends StatelessWidget {
  const _Choice({
    required this.label,
    required this.icon,
    required this.color,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final IconData icon;
  final Color color;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: SwitchListTile(
        value: value,
        onChanged: onChanged,
        activeColor: color,
        title: Text(label),
        secondary: Icon(icon, color: color),
      ),
    );
  }
}
