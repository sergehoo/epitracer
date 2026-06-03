import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class VaccinationsScreen extends StatelessWidget {
  const VaccinationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Carnet de vaccination')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {},
        icon: const Icon(Icons.add),
        label: const Text('Ajouter'),
        backgroundColor: AppColors.ciOrange,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          _VaccineCard(
            disease: 'Fièvre jaune',
            vaccine: 'STAMARIL',
            date: '15/03/2024',
            verified: true,
          ),
          SizedBox(height: 12),
          _VaccineCard(
            disease: 'Covid-19',
            vaccine: 'AstraZeneca — dose 3',
            date: '08/01/2024',
            verified: true,
          ),
        ],
      ),
    );
  }
}

class _VaccineCard extends StatelessWidget {
  const _VaccineCard({
    required this.disease,
    required this.vaccine,
    required this.date,
    required this.verified,
  });

  final String disease;
  final String vaccine;
  final String date;
  final bool verified;

  @override
  Widget build(BuildContext context) {
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
        title: Text(disease, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('$vaccine\n$date',
            style: const TextStyle(color: AppColors.slate500)),
        isThreeLine: true,
        trailing: verified
            ? const Icon(Icons.verified, color: AppColors.statusOk)
            : null,
      ),
    );
  }
}
