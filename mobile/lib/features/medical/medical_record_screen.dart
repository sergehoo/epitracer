import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/medical_record.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/glass_card.dart';
import '../../shared/widgets/offline_banner.dart';
import 'medical_repository.dart';

class MedicalRecordScreen extends ConsumerWidget {
  const MedicalRecordScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(medicalRecordProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Carnet de santé'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            onPressed: () {
              final r = async.asData?.value ?? const MedicalRecord();
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => MedicalRecordEditScreen(initial: r),
                  fullscreenDialog: true,
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const Center(child: Text('Erreur')),
              data: (rec) => _RecordView(rec: rec),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecordView extends StatelessWidget {
  const _RecordView({required this.rec});
  final MedicalRecord rec;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: AppGradients.ciFlag,
            borderRadius: BorderRadius.circular(24),
            boxShadow: AppShadows.elevated(AppColors.ciOrange, opacity: 0.25),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.bloodtype,
                  color: Colors.white,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rec.bloodType ?? '—',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      rec.organDonor
                          ? 'Donneur d\'organes'
                          : 'Groupe sanguin',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              if (rec.bmi != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.22),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    'IMC ${rec.bmi!.toStringAsFixed(1)}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: _MiniInfo(
                icon: Icons.height,
                label: 'Taille',
                value: rec.heightCm != null ? '${rec.heightCm} cm' : '—',
                color: AppColors.ciGreen,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _MiniInfo(
                icon: Icons.monitor_weight_outlined,
                label: 'Poids',
                value: rec.weightKg != null
                    ? '${rec.weightKg!.toStringAsFixed(1)} kg'
                    : '—',
                color: AppColors.ciOrange,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _ListSection(
          title: 'Allergies',
          icon: Icons.warning_amber_rounded,
          color: AppColors.statusDanger,
          items: rec.allergies,
          empty: 'Aucune allergie déclarée',
        ),
        const SizedBox(height: 12),
        _ListSection(
          title: 'Maladies chroniques',
          icon: Icons.medical_information_outlined,
          color: AppColors.statusWarn,
          items: rec.chronicConditions,
          empty: 'Aucune affection chronique',
        ),
        const SizedBox(height: 12),
        _ListSection(
          title: 'Médicaments actuels',
          icon: Icons.medication_outlined,
          color: AppColors.statusInfo,
          items: rec.currentMedications,
          empty: 'Aucun traitement en cours',
        ),
        const SizedBox(height: 12),
        _ListSection(
          title: 'Antécédents chirurgicaux',
          icon: Icons.healing,
          color: AppColors.inhpBlue,
          items: rec.previousSurgeries,
          empty: 'Aucun antécédent',
        ),
        const SizedBox(height: 16),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: const [
                  Icon(Icons.contact_phone, color: AppColors.ciOrange, size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Contacts d\'urgence',
                    style:
                        TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (rec.emergencyContacts.isEmpty)
                const Text(
                  'Aucun contact enregistré',
                  style: TextStyle(color: AppColors.slate500, fontSize: 13),
                )
              else
                for (final c in rec.emergencyContacts)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      children: [
                        const Icon(Icons.person,
                            color: AppColors.slate500, size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                c.name,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600),
                              ),
                              Text(
                                '${c.phone}${c.relation != null ? " · ${c.relation}" : ""}',
                                style: const TextStyle(
                                    color: AppColors.slate500, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.phone,
                              color: AppColors.ciGreen, size: 20),
                          onPressed: () {/* launch tel: */},
                        ),
                      ],
                    ),
                  ),
            ],
          ),
        ),
        if (rec.notes != null && rec.notes!.isNotEmpty) ...[
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.note_alt_outlined,
                        color: AppColors.slate500, size: 18),
                    SizedBox(width: 8),
                    Text('Notes',
                        style: TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 14)),
                  ],
                ),
                const SizedBox(height: 8),
                Text(rec.notes!),
              ],
            ),
          ),
        ],
        const SizedBox(height: 24),
      ],
    );
  }
}

class _MiniInfo extends StatelessWidget {
  const _MiniInfo({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: const TextStyle(
                        color: AppColors.slate500, fontSize: 11)),
                Text(value,
                    style: const TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 16)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ListSection extends StatelessWidget {
  const _ListSection({
    required this.title,
    required this.icon,
    required this.color,
    required this.items,
    required this.empty,
  });

  final String title;
  final IconData icon;
  final Color color;
  final List<String> items;
  final String empty;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(title,
                  style:
                      const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
            ],
          ),
          const SizedBox(height: 10),
          if (items.isEmpty)
            Text(empty,
                style: const TextStyle(
                    color: AppColors.slate500, fontSize: 13))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: items
                  .map(
                    (s) => Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                        border:
                            Border.all(color: color.withValues(alpha: 0.25)),
                      ),
                      child: Text(
                        s,
                        style: TextStyle(
                          color: color,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }
}

/// Édition multi-section du carnet de santé.
class MedicalRecordEditScreen extends ConsumerStatefulWidget {
  const MedicalRecordEditScreen({super.key, required this.initial});
  final MedicalRecord initial;

  @override
  ConsumerState<MedicalRecordEditScreen> createState() =>
      _MedicalRecordEditScreenState();
}

class _MedicalRecordEditScreenState
    extends ConsumerState<MedicalRecordEditScreen> {
  late String? _bloodType;
  late TextEditingController _height;
  late TextEditingController _weight;
  late TextEditingController _allergies;
  late TextEditingController _chronic;
  late TextEditingController _meds;
  late TextEditingController _surgeries;
  late TextEditingController _notes;
  late bool _organDonor;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _bloodType = widget.initial.bloodType;
    _height = TextEditingController(
        text: widget.initial.heightCm?.toString() ?? '');
    _weight = TextEditingController(
        text: widget.initial.weightKg?.toString() ?? '');
    _allergies =
        TextEditingController(text: widget.initial.allergies.join(', '));
    _chronic = TextEditingController(
        text: widget.initial.chronicConditions.join(', '));
    _meds = TextEditingController(
        text: widget.initial.currentMedications.join(', '));
    _surgeries = TextEditingController(
        text: widget.initial.previousSurgeries.join(', '));
    _notes = TextEditingController(text: widget.initial.notes ?? '');
    _organDonor = widget.initial.organDonor;
  }

  @override
  void dispose() {
    _height.dispose();
    _weight.dispose();
    _allergies.dispose();
    _chronic.dispose();
    _meds.dispose();
    _surgeries.dispose();
    _notes.dispose();
    super.dispose();
  }

  List<String> _split(String raw) => raw
      .split(',')
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toList();

  Future<void> _save() async {
    setState(() => _saving = true);
    final updated = widget.initial.copyWith(
      bloodType: _bloodType,
      heightCm: int.tryParse(_height.text.trim()),
      weightKg: double.tryParse(_weight.text.trim().replaceAll(',', '.')),
      allergies: _split(_allergies.text),
      chronicConditions: _split(_chronic.text),
      currentMedications: _split(_meds.text),
      previousSurgeries: _split(_surgeries.text),
      notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
      organDonor: _organDonor,
    );
    final ok = await ref.read(medicalRepositoryProvider).save(updated);
    ref.invalidate(medicalRecordProvider);
    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? 'Carnet de santé mis à jour'
          : 'Sauvegardé hors-ligne — sync au retour'),
    ));
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Modifier mon carnet'),
        actions: [
          TextButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Enregistrer'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          DropdownButtonFormField<String>(
            value: _bloodType,
            decoration: const InputDecoration(labelText: 'Groupe sanguin'),
            items: kBloodTypes
                .map((b) => DropdownMenuItem(value: b, child: Text(b)))
                .toList(),
            onChanged: (v) => setState(() => _bloodType = v),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _height,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Taille (cm)'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _weight,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  decoration: const InputDecoration(labelText: 'Poids (kg)'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _MultilineField(
            label: 'Allergies (séparées par virgule)',
            controller: _allergies,
          ),
          _MultilineField(
            label: 'Maladies chroniques',
            controller: _chronic,
          ),
          _MultilineField(
            label: 'Médicaments actuels',
            controller: _meds,
          ),
          _MultilineField(
            label: 'Antécédents chirurgicaux',
            controller: _surgeries,
          ),
          _MultilineField(
            label: 'Notes médicales libres',
            controller: _notes,
            maxLines: 4,
          ),
          SwitchListTile(
            value: _organDonor,
            onChanged: (v) => setState(() => _organDonor = v),
            title: const Text('Je suis donneur d\'organes'),
            secondary: const Icon(Icons.volunteer_activism,
                color: AppColors.ciGreen),
            activeColor: AppColors.ciGreen,
            contentPadding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }
}

class _MultilineField extends StatelessWidget {
  const _MultilineField({
    required this.label,
    required this.controller,
    this.maxLines = 2,
  });

  final String label;
  final TextEditingController controller;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: controller,
        maxLines: maxLines,
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}
