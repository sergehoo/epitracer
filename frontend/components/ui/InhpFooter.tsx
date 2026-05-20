import Link from 'next/link';
import { PhoneCall } from 'lucide-react';
import { adminUrl } from '@/lib/hosts';

export function InhpFooter() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <div className="container py-10 grid gap-8 md:grid-cols-3">
        <div>
          <div className="font-display text-lg font-bold">EpiTravel</div>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Plateforme officielle de surveillance épidémiologique des voyageurs entrant
            sur le territoire ivoirien.
          </p>
          <p className="mt-3 text-xs text-slate-400">
            © {new Date().getFullYear()} République de Côte d'Ivoire — MINSAN · INHP.
          </p>
        </div>

        <div>
          <div className="text-sm font-semibold mb-2">Navigation</div>
          <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
            <li><Link href="/voyageur" className="hover:text-emerald-600">Enregistrer mon arrivée</Link></li>
            <li><Link href="/pass" className="hover:text-emerald-600">Récupérer mon pass</Link></li>
            <li><Link href="/verifier" className="hover:text-emerald-600">Vérifier un QR</Link></li>
            <li><Link href="/assistance" className="hover:text-emerald-600">Assistance</Link></li>
            <li><a href={adminUrl('/auth/login')} className="hover:text-emerald-600">Espace professionnel</a></li>
          </ul>
        </div>

        <div>
          <div className="text-sm font-semibold mb-2">Numéros d'urgence</div>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              <PhoneCall className="h-4 w-4 text-emerald-600" />
              <span>SAMU National (gratuit) :</span>
              <a href="tel:185" className="font-semibold">185</a>
            </li>
            <li className="flex items-center gap-2">
              <PhoneCall className="h-4 w-4 text-emerald-600" />
              <span>Allô Santé :</span>
              <a href="tel:143" className="font-semibold">143</a>
            </li>
            <li className="flex items-center gap-2">
              <PhoneCall className="h-4 w-4 text-emerald-600" />
              <span>Centre de Secours :</span>
              <a href="tel:101" className="font-semibold">101</a>
            </li>
            <li className="text-xs text-slate-500 dark:text-slate-400 mt-3">
              INHP — 27 21 25 35 10 / 27 21 25 97 46<br />
              episurvinhp@gmail.com
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
