import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/glass_card.dart';

class _Practitioner {
  const _Practitioner({
    required this.name,
    required this.specialty,
    required this.org,
    required this.phone,
    required this.whatsapp,
    this.available = true,
  });
  final String name;
  final String specialty;
  final String org;
  final String phone;
  final String whatsapp;
  final bool available;
}

/// Liste statique des contacts officiels INHP / MSHPCMU.
/// À synchroniser avec un endpoint backend dans une prochaine version,
/// mais ces numéros sont publics et stables (annuaire INHP).
const List<_Practitioner> _kPractitioners = [
  _Practitioner(
    name: 'Centre d\'appel INHP',
    specialty: 'Information sanitaire générale',
    org: 'INHP — Treichville',
    phone: '143',
    whatsapp: '+2250143',
  ),
  _Practitioner(
    name: 'SAMU National',
    specialty: 'Urgences médicales 24h/24',
    org: 'Ministère de la Santé',
    phone: '185',
    whatsapp: '+2250185',
  ),
  _Practitioner(
    name: 'Cellule Veille Sanitaire',
    specialty: 'Suivi épidémiologique des voyageurs',
    org: 'INHP — Pôle surveillance',
    phone: '+2252124005',
    whatsapp: '+22507000000',
  ),
];

class TeleconsultScreen extends StatelessWidget {
  const TeleconsultScreen({super.key});

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _whatsapp(String phone) async {
    final normalized = phone.replaceAll(RegExp(r'\s+'), '');
    final msg = Uri.encodeComponent(
      'Bonjour, je suis voyageur enregistré sur Mon Pass Sanitaire et j\'aimerais un conseil sanitaire INHP. Merci.',
    );
    final uri = Uri.parse('https://wa.me/$normalized?text=$msg');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Téléconsultation INHP')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          // Bandeau d'intro
          Container(
            margin: const EdgeInsets.symmetric(vertical: 12),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: AppGradients.healthyGreen,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppShadows.elevated(AppColors.ciGreen),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.22),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.medical_services,
                      color: Colors.white, size: 28),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Vous n\'êtes pas seul',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          )),
                      SizedBox(height: 4),
                      Text(
                        'Un professionnel INHP peut vous orienter par téléphone ou WhatsApp.',
                        style: TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Liste des contacts
          for (final p in _kPractitioners) ...[
            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 22,
                        backgroundColor:
                            AppColors.ciOrange.withValues(alpha: 0.15),
                        child: const Icon(Icons.local_hospital,
                            color: AppColors.ciOrange, size: 24),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(p.name,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w800, fontSize: 15)),
                            const SizedBox(height: 2),
                            Text(p.specialty,
                                style: const TextStyle(
                                    color: AppColors.slate500, fontSize: 12)),
                            const SizedBox(height: 2),
                            Text(p.org,
                                style: const TextStyle(
                                    color: AppColors.slate500,
                                    fontSize: 11,
                                    fontStyle: FontStyle.italic)),
                          ],
                        ),
                      ),
                      if (p.available)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppColors.statusOk.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'Dispo',
                            style: TextStyle(
                              color: AppColors.statusOk,
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _call(p.phone),
                          icon: const Icon(Icons.phone, size: 16),
                          label: Text(p.phone),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppColors.ciDark,
                            side: const BorderSide(color: AppColors.ciDark),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _whatsapp(p.whatsapp),
                          icon: const Icon(Icons.chat, size: 16),
                          label: const Text('WhatsApp'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.ciGreen,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.statusInfo.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppColors.statusInfo.withValues(alpha: 0.25),
              ),
            ),
            child: Row(
              children: const [
                Icon(Icons.info_outline,
                    color: AppColors.statusInfo, size: 18),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'En cas d\'urgence vitale, appelez directement le 185 (SAMU). Les autres numéros sont opérationnels en heures ouvrées.',
                    style: TextStyle(
                        color: AppColors.statusInfo, fontSize: 12),
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
