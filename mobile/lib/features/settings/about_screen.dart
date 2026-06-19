import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';
import '../../shared/widgets/afriq_credit_footer.dart';

const String kAppVersion = '1.0.0';
const String kAppBuild = '1';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  Future<void> _open(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('À propos')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          // Bandeau institutionnel
          const OfficialLogosBanner(size: 56),
          const SizedBox(height: 20),
          // Logo + version
          Center(
            child: Column(
              children: [
                Container(
                  height: 96,
                  width: 96,
                  decoration: BoxDecoration(
                    gradient: AppGradients.healthyGreen,
                    borderRadius: BorderRadius.circular(28),
                    boxShadow: AppShadows.elevated(AppColors.ciGreen),
                  ),
                  child: const Icon(
                    Icons.health_and_safety,
                    color: Colors.white,
                    size: 56,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Mon Pass Sanitaire',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: AppColors.ciDark,
                  ),
                ),
                Text(
                  'Version $kAppVersion ($kAppBuild)',
                  style: const TextStyle(
                    color: AppColors.slate500,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          const Text(
            'À propos de cette application',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
          ),
          const SizedBox(height: 8),
          const Text(
            "Mon Pass Sanitaire est l'application officielle de l'Institut National "
            "d'Hygiène Publique (INHP) de Côte d'Ivoire. Elle permet aux voyageurs "
            "internationaux de consulter leur pass sanitaire, déclarer leur état "
            "quotidien, et accéder à un accompagnement santé pendant leur séjour.",
            style: TextStyle(fontSize: 13, height: 1.5, color: AppColors.slate700),
          ),

          const SizedBox(height: 24),
          const Text(
            'Institutions',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
          ),
          const SizedBox(height: 8),
          _LinkTile(
            icon: Icons.account_balance,
            title: 'Ministère de la Santé (MSHPCMU)',
            subtitle: 'sante.gouv.ci',
            onTap: () => _open('https://www.sante.gouv.ci'),
          ),
          _LinkTile(
            icon: Icons.local_hospital,
            title: 'Institut National d\'Hygiène Publique',
            subtitle: 'inhp.ci',
            onTap: () => _open('https://www.inhp.ci'),
          ),

          const SizedBox(height: 24),
          const Text(
            'Contact',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
          ),
          const SizedBox(height: 8),
          _LinkTile(
            icon: Icons.phone,
            title: 'Numéro vert INHP',
            subtitle: '143 (24h/24, gratuit)',
            onTap: () => _open('tel:143'),
          ),
          _LinkTile(
            icon: Icons.local_hospital,
            title: 'SAMU National',
            subtitle: '185',
            onTap: () => _open('tel:185'),
          ),
          _LinkTile(
            icon: Icons.email_outlined,
            title: 'Support',
            subtitle: 'info@destinationci.com',
            onTap: () => _open('mailto:info@destinationci.com'),
          ),

          const SizedBox(height: 24),
          const Text(
            'Sécurité & confidentialité',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
          ),
          const SizedBox(height: 8),
          _LinkTile(
            icon: Icons.shield_outlined,
            title: 'Politique de confidentialité',
            subtitle: 'Comment vos données sont protégées',
            onTap: () => _open('https://veillesanitaire.com/privacy'),
          ),
          _LinkTile(
            icon: Icons.gavel,
            title: 'Conditions d\'utilisation',
            subtitle: 'CGU',
            onTap: () => _open('https://veillesanitaire.com/cgu'),
          ),

          const SizedBox(height: 32),
          Center(
            child: Column(
              children: [
                Text(
                  '© ${DateTime.now().year} République de Côte d\'Ivoire',
                  style: const TextStyle(
                    color: AppColors.slate500,
                    fontSize: 11,
                  ),
                ),
                const Text(
                  'MSHPCMU · INHP',
                  style: TextStyle(color: AppColors.slate500, fontSize: 11),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Tous droits réservés.',
                  style: TextStyle(color: AppColors.slate300, fontSize: 10),
                ),
                const SizedBox(height: 16),
                const Divider(color: AppColors.slate200, height: 1),
                const AfriqCreditFooter(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LinkTile extends StatelessWidget {
  const _LinkTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 3),
      child: ListTile(
        leading: Icon(icon, color: AppColors.ciOrange),
        title: Text(title,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
