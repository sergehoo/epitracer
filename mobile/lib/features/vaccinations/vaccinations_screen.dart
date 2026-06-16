import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/models/vaccination.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/offline_banner.dart';
import 'vaccinations_repository.dart';

class VaccinationsScreen extends ConsumerWidget {
  const VaccinationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(vaccinationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Carnet de vaccination')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddSheet(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Ajouter'),
        backgroundColor: AppColors.ciOrange,
      ),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const _ErrorState(),
              data: (list) {
                if (list.isEmpty) return const _EmptyState();
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(vaccinationsProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (_, i) => _VaccineCard(v: list[i]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showAddSheet(BuildContext context, WidgetRef ref) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _AddVaccinationSheet(),
    );
    ref.invalidate(vaccinationsProvider);
  }
}

class _VaccineCard extends StatelessWidget {
  const _VaccineCard({required this.v});
  final Vaccination v;

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy');
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(12),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.ciGreen.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.vaccines, color: AppColors.ciGreen),
        ),
        title: Text(
          v.diseaseName.isNotEmpty ? v.diseaseName : v.diseaseCode,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        subtitle: Text(
          '${v.vaccineName} — dose ${v.doseNumber}/${v.totalDoses}\n${df.format(v.administeredAt)}',
          style: const TextStyle(color: AppColors.slate500),
        ),
        isThreeLine: true,
        trailing: v.verified
            ? const Icon(Icons.verified, color: AppColors.statusOk)
            : const Icon(Icons.hourglass_empty, color: AppColors.slate300),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.vaccines, size: 72, color: AppColors.slate300),
            SizedBox(height: 12),
            Text('Carnet vide',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            SizedBox(height: 6),
            Text(
              'Ajoutez vos vaccinations pour les conserver hors-ligne.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.slate500),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState();
  @override
  Widget build(BuildContext context) => const Center(
        child: Text('Erreur de chargement',
            style: TextStyle(color: AppColors.slate500)),
      );
}

class _AddVaccinationSheet extends ConsumerStatefulWidget {
  @override
  ConsumerState<_AddVaccinationSheet> createState() => _AddVaccinationSheetState();
}

class _AddVaccinationSheetState extends ConsumerState<_AddVaccinationSheet> {
  final _disease = TextEditingController();
  final _vaccine = TextEditingController();
  DateTime _date = DateTime.now();
  bool _saving = false;

  @override
  void dispose() {
    _disease.dispose();
    _vaccine.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_disease.text.trim().isEmpty || _vaccine.text.trim().isEmpty) return;
    setState(() => _saving = true);
    final ok = await ref.read(vaccinationsRepositoryProvider).create({
      'disease_code': _disease.text.trim().toUpperCase(),
      'disease_name': _disease.text.trim(),
      'vaccine_name': _vaccine.text.trim(),
      'administered_at': _date.toIso8601String(),
      'dose_number': 1,
      'total_doses': 1,
    });
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok != null
          ? 'Vaccination enregistrée'
          : 'Sauvegardée hors-ligne — sync au retour de la connexion'),
    ));
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy');
    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Nouvelle vaccination',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
          const SizedBox(height: 16),
          TextField(
            controller: _disease,
            decoration: const InputDecoration(labelText: 'Maladie'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _vaccine,
            decoration: const InputDecoration(labelText: 'Vaccin'),
          ),
          const SizedBox(height: 12),
          InkWell(
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: _date,
                firstDate: DateTime(2000),
                lastDate: DateTime.now(),
              );
              if (picked != null) setState(() => _date = picked);
            },
            child: InputDecorator(
              decoration: const InputDecoration(labelText: 'Date'),
              child: Text(df.format(_date)),
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(height: 18, width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Enregistrer'),
          ),
        ],
      ),
    );
  }
}
