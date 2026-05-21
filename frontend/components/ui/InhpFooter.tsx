import Link from 'next/link';
import { adminUrl } from '@/lib/hosts';

export function InhpFooter() {
  return (
    <footer className="bg-ciDark text-white">
      <div className="max-w-7xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
        <div>
          <h4 className="font-display font-black text-xl">EpiTravel CI</h4>
          <p className="mt-3 text-sm text-emerald-100/90 leading-6">
            Plateforme nationale d'accompagnement sanitaire des voyageurs entrant
            sur le territoire ivoirien.
          </p>
          <p className="mt-4 text-xs text-emerald-100/60">
            © {new Date().getFullYear()} République de Côte d'Ivoire — MINSAN · INHP.
          </p>
        </div>

        <div>
          <h5 className="font-bold mb-3">Voyageur</h5>
          <ul className="space-y-2 text-sm text-emerald-100/90">
            <li><Link href="/voyageur" className="hover:text-ciOrange transition">Préparer mon arrivée</Link></li>
            <li><Link href="/pass" className="hover:text-ciOrange transition">Vérifier mon pass</Link></li>
            <li><Link href="/verifier" className="hover:text-ciOrange transition">Vérifier un QR</Link></li>
            <li><Link href="/assistance" className="hover:text-ciOrange transition">Conseils sanitaires</Link></li>
          </ul>
        </div>

        <div>
          <h5 className="font-bold mb-3">Institutionnel</h5>
          <ul className="space-y-2 text-sm text-emerald-100/90">
            <li><a href="https://www.sante.gouv.ci" target="_blank" rel="noreferrer" className="hover:text-ciOrange transition">Ministère de la Santé</a></li>
            <li><a href="https://www.inhp.ci" target="_blank" rel="noreferrer" className="hover:text-ciOrange transition">INHP</a></li>
            <li><Link href="/#fonctionnement" className="hover:text-ciOrange transition">Points d'entrée</Link></li>
            <li><a href={adminUrl('/auth/login')} className="hover:text-ciOrange transition">Espace professionnel</a></li>
          </ul>
        </div>

        <div>
          <h5 className="font-bold mb-3">Numéros d'urgence</h5>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between border-b border-white/10 pb-2">
              <span className="text-emerald-100/90">SAMU National</span>
              <a href="tel:185" className="font-black text-ciOrange">185</a>
            </li>
            <li className="flex items-center justify-between border-b border-white/10 pb-2">
              <span className="text-emerald-100/90">Allô Santé</span>
              <a href="tel:143" className="font-black text-ciOrange">143</a>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-emerald-100/90">Secours</span>
              <a href="tel:101" className="font-black text-ciOrange">101</a>
            </li>
          </ul>
          <p className="mt-4 text-xs text-emerald-100/60">
            INHP · 27 21 25 35 10 / 27 21 25 97 46<br />
            episurvinhp@gmail.com
          </p>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-2 text-xs text-emerald-100/70">
          <span>Tous droits réservés.</span>
          <span>Données protégées · Signature cryptographique Ed25519</span>
        </div>
      </div>
    </footer>
  );
}
