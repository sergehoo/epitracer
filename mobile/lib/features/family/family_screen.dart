import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/models/family_member.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/glass_card.dart';
import '../../shared/widgets/offline_banner.dart';
import 'family_repository.dart';

class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(familyProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Ma famille')),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.ciOrange,
        onPressed: () => _showAddSheet(context, ref),
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text('Ajouter un proche'),
      ),
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => const Center(child: Text('Erreur')),
              data: (list) {
                if (list.isEmpty) return const _EmptyState();
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                  itemCount: list.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, i) => _MemberCard(
                    member: list[i],
                    onDelete: () async {
                      final ok = await ref
                          .read(familyRepositoryProvider)
                          .remove(list[i].id);
                      if (ok) ref.invalidate(familyProvider);
                    },
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
      builder: (_) => const _AddMemberSheet(),
    );
    ref.invalidate(familyProvider);
  }
}

class _MemberCard extends StatelessWidget {
  const _MemberCard({required this.member, required this.onDelete});
  final FamilyMember member;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Row(
        children: [
          Container(
            height: 56,
            width: 56,
            decoration: BoxDecoration(
              gradient: AppGradients.ciFlag,
              shape: BoxShape.circle,
              boxShadow: AppShadows.soft(AppColors.ciOrange),
            ),
            alignment: Alignment.center,
            child: Text(
              member.initials,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 18,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  member.fullName,
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 15),
                ),
                const SizedBox(height: 2),
                Text(
                  '${member.relation.label}${member.age != null ? " · ${member.age} ans" : ""}',
                  style: const TextStyle(
                      color: AppColors.slate500, fontSize: 12),
                ),
                if (member.bloodType != null) ...[
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.statusDanger.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${member.bloodType}',
                      style: const TextStyle(
                        color: AppColors.statusDanger,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'delete') onDelete();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'delete', child: Text('Retirer')),
            ],
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Icon(Icons.family_restroom,
                  size: 80, color: AppColors.slate300),
              SizedBox(height: 16),
              Text(
                'Aucun proche enregistré',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              SizedBox(height: 6),
              Text(
                'Ajoutez votre conjoint(e), vos enfants ou parents pour gérer leurs pass et suivis sanitaires depuis votre compte.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.slate500),
              ),
            ],
          ),
        ),
      );
}

class _AddMemberSheet extends ConsumerStatefulWidget {
  const _AddMemberSheet();

  @override
  ConsumerState<_AddMemberSheet> createState() => _AddMemberSheetState();
}

class _AddMemberSheetState extends ConsumerState<_AddMemberSheet> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  FamilyRelation _relation = FamilyRelation.child;
  String? _blood;
  DateTime? _dob;
  bool _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) return;
    setState(() => _saving = true);
    final m = FamilyMember(
      id: '',
      fullName: _name.text.trim(),
      relation: _relation,
      phone: _phone.text.trim().isEmpty ? null : _phone.text.trim(),
      bloodType: _blood,
      dateOfBirth: _dob,
      isMinor:
          _dob != null && DateTime.now().difference(_dob!).inDays < 365 * 18,
    );
    await ref.read(familyRepositoryProvider).create(m);
    if (!mounted) return;
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy');
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Ajouter un proche',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'Nom complet'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<FamilyRelation>(
            value: _relation,
            decoration: const InputDecoration(labelText: 'Lien de parenté'),
            items: FamilyRelation.values
                .where((r) => r != FamilyRelation.self)
                .map((r) =>
                    DropdownMenuItem(value: r, child: Text(r.label)))
                .toList(),
            onChanged: (v) => setState(() => _relation = v ?? _relation),
          ),
          const SizedBox(height: 12),
          InkWell(
            onTap: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: DateTime.now().subtract(const Duration(days: 365 * 8)),
                firstDate: DateTime(1900),
                lastDate: DateTime.now(),
              );
              if (picked != null) setState(() => _dob = picked);
            },
            child: InputDecorator(
              decoration: const InputDecoration(labelText: 'Date de naissance'),
              child: Text(_dob != null ? df.format(_dob!) : 'Non renseignée'),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
                labelText: 'Téléphone (optionnel)'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _blood,
            decoration: const InputDecoration(labelText: 'Groupe sanguin'),
            items: const ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
                .map((b) => DropdownMenuItem(value: b, child: Text(b)))
                .toList(),
            onChanged: (v) => setState(() => _blood = v),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(
                    height: 16,
                    width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Ajouter à ma famille'),
          ),
        ],
      ),
    );
  }
}
