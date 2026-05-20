import Link from 'next/link';
import {
  Activity, ArrowRight, FileCheck2, HeartPulse, MapPinned,
  PhoneCall, QrCode, ShieldCheck, Stethoscope, TimerReset,
} from 'lucide-react';
import { Section } from '@/components/ui/Section';

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-br from-emerald-50 via-white to-orange-50 dark:from-emerald-950/40 dark:via-slate-950 dark:to-orange-950/30" />
        <div className="container py-16 lg:py-24 grid lg:grid-cols-2 gap-12 items-center">
          <div className="animate-fade-up">
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200/70 dark:ring-emerald-800">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-dot" />
              Plateforme officielle de l'INHP
            </div>
            <h1 className="mt-5 font-display text-4xl lg:text-6xl font-extrabold tracking-tight">
              Surveillance sanitaire <span className="text-emerald-600">à l'arrivée</span> sur le territoire ivoirien.
            </h1>
            <p className="mt-5 text-lg text-slate-600 dark:text-slate-300 max-w-xl">
              Enregistrez votre fiche passager Ebola en ligne, recevez immédiatement votre
              <strong> pass sanitaire QR code</strong> et bénéficiez d'un suivi de 21 jours
              conformément aux directives de santé publique.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/voyageur" className="btn-primary text-base">
                Démarrer mon enregistrement
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/pass" className="btn-outline text-base">
                <QrCode className="h-4 w-4" />
                Récupérer mon pass
              </Link>
            </div>
            <div className="mt-6 flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Données chiffrées · Signature cryptographique Ed25519 · Vérifiable hors-ligne
            </div>
          </div>

          <div className="relative">
            <div className="card p-6 lg:p-8 max-w-md ml-auto">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-emerald-600 font-semibold">Pass sanitaire</div>
                  <div className="font-display text-lg font-bold">TRV-XXXXXXXXXX</div>
                </div>
                <div className="badge-low">FAIBLE · 8/100</div>
              </div>
              <div className="aspect-square w-full max-w-[260px] mx-auto rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 grid place-items-center text-white shadow-glow">
                <QrCode className="h-28 w-28" />
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900 p-3 border border-slate-200/50 dark:border-slate-800">
                  <dt className="text-slate-500">Maladie suivie</dt>
                  <dd className="font-semibold mt-0.5">Ebola (MVE)</dd>
                </div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900 p-3 border border-slate-200/50 dark:border-slate-800">
                  <dt className="text-slate-500">Surveillance</dt>
                  <dd className="font-semibold mt-0.5">21 jours</dd>
                </div>
                <div className="col-span-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 p-3 border border-emerald-200/60 dark:border-emerald-900">
                  <dt className="text-emerald-700 dark:text-emerald-300">Émetteur</dt>
                  <dd className="font-semibold mt-0.5 text-slate-900 dark:text-slate-100">MINSAN-CI · INHP</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </section>

      {/* Comment ça marche */}
      <Section
        eyebrow="Comment ça marche"
        title="Trois étapes pour valider votre arrivée"
        description="Le portail vous accompagne avant, pendant et après votre arrivée en Côte d'Ivoire."
      >
        <div className="grid md:grid-cols-3 gap-5">
          {[
            {
              icon: <FileCheck2 className="h-6 w-6" />, n: '01',
              title: 'Remplissez la fiche passager',
              desc: 'Saisissez les 7 sections de la fiche officielle INHP : voyage, identité, historique, confinement, exposition, symptômes, déclaration.',
              link: '/voyageur', label: 'Remplir',
            },
            {
              icon: <QrCode className="h-6 w-6" />, n: '02',
              title: 'Recevez votre pass QR',
              desc: 'Un pass sanitaire numérique signé est généré immédiatement. Affichez-le à l\'arrivée pour contrôle aux frontières.',
              link: '/pass', label: 'Voir mon pass',
            },
            {
              icon: <HeartPulse className="h-6 w-6" />, n: '03',
              title: 'Suivi sanitaire 21 jours',
              desc: 'L\'INHP organise un suivi pendant la durée d\'incubation maximale. Signalez tout symptôme via les numéros d\'urgence.',
              link: '/assistance', label: 'Assistance',
            },
          ].map((s) => (
            <article key={s.n} className="card p-6 group hover:-translate-y-0.5 transition">
              <div className="flex items-center justify-between">
                <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600 text-white">{s.icon}</div>
                <span className="font-display text-3xl font-extrabold text-slate-200 dark:text-slate-800">{s.n}</span>
              </div>
              <h3 className="mt-4 font-display text-lg font-bold">{s.title}</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{s.desc}</p>
              <Link href={s.link} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-emerald-700 dark:text-emerald-400 group-hover:gap-2 transition-all">
                {s.label} <ArrowRight className="h-4 w-4" />
              </Link>
            </article>
          ))}
        </div>
      </Section>

      {/* Bandeau Ebola */}
      <Section
        className="!pt-0"
        eyebrow="Information sanitaire"
        title="Maladie à Virus Ebola (MVE)"
        description="Infection grave provoquée par le virus Ebola. Incubation jusqu'à 21 jours, transmission par contact direct avec les fluides corporels d'une personne ou animale infectée."
      >
        <div className="grid lg:grid-cols-3 gap-5">
          <div className="card p-6">
            <Stethoscope className="h-6 w-6 text-emerald-600" />
            <h3 className="mt-3 font-display text-lg font-bold">Symptômes à surveiller</h3>
            <ul className="mt-3 text-sm space-y-2 text-slate-700 dark:text-slate-200">
              <li>· Fièvre brutale (≥ 38°C)</li>
              <li>· Fatigue intense, douleurs musculaires</li>
              <li>· Maux de tête, maux de gorge</li>
              <li>· Diarrhée, vomissements</li>
              <li>· Saignements inexpliqués (red flag)</li>
            </ul>
          </div>
          <div className="card p-6">
            <Activity className="h-6 w-6 text-emerald-600" />
            <h3 className="mt-3 font-display text-lg font-bold">Mesures de prévention</h3>
            <ul className="mt-3 text-sm space-y-2 text-slate-700 dark:text-slate-200">
              <li>· Lavage fréquent des mains</li>
              <li>· Éviter tout contact avec personnes fébriles</li>
              <li>· Pas de rite funéraire de lavage mortuaire</li>
              <li>· Ne pas consommer de viande de brousse</li>
            </ul>
          </div>
          <div className="card p-6">
            <TimerReset className="h-6 w-6 text-emerald-600" />
            <h3 className="mt-3 font-display text-lg font-bold">Suivi obligatoire 21 jours</h3>
            <p className="mt-3 text-sm text-slate-700 dark:text-slate-200">
              Conformément aux directives, les voyageurs provenant de zones à risque font l'objet d'un
              suivi de 21 jours par l'INHP. Restez joignable à l'adresse de confinement déclarée.
            </p>
          </div>
        </div>
      </Section>

      {/* Bandeau urgence */}
      <section className="bg-rose-600 text-white">
        <div className="container py-10 grid md:grid-cols-3 gap-6 items-center">
          <div>
            <div className="text-xs uppercase tracking-widest opacity-90">Symptômes évocateurs ?</div>
            <h3 className="font-display text-2xl font-extrabold mt-1">Composez immédiatement un de ces numéros</h3>
          </div>
          <div className="md:col-span-2 grid sm:grid-cols-3 gap-3">
            {[
              { label: 'SAMU', number: '185', sub: 'Appel gratuit' },
              { label: 'Allô Santé', number: '143', sub: 'Ministère de la Santé' },
              { label: 'Secours', number: '101', sub: 'Police / Secours' },
            ].map((p) => (
              <a key={p.number} href={`tel:${p.number}`} className="rounded-2xl bg-white/10 hover:bg-white/15 transition p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold opacity-90">{p.label}</div>
                  <div className="text-xs opacity-80">{p.sub}</div>
                </div>
                <div className="flex items-center gap-2 text-2xl font-bold">
                  <PhoneCall className="h-5 w-5" />
                  {p.number}
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* Carte couverture */}
      <Section
        eyebrow="Couverture nationale"
        title="Points d'entrée sanitaires surveillés"
        description="Aéroports, ports et frontières terrestres équipés du dispositif de surveillance épidémiologique."
      >
        <div className="grid md:grid-cols-3 gap-5">
          {[
            { name: 'Aéroport FHB Abidjan', sub: 'ABJ · DIAP', icon: <MapPinned className="h-5 w-5" /> },
            { name: 'Port Autonome d\'Abidjan', sub: 'Port maritime', icon: <MapPinned className="h-5 w-5" /> },
            { name: 'Port de San-Pédro', sub: 'Port maritime', icon: <MapPinned className="h-5 w-5" /> },
            { name: 'Frontière de Pôgô', sub: 'CI / Mali', icon: <MapPinned className="h-5 w-5" /> },
            { name: 'Frontière de Niablé', sub: 'CI / Ghana', icon: <MapPinned className="h-5 w-5" /> },
            { name: 'Aéroport de Yamoussoukro', sub: 'ASK · DIYO', icon: <MapPinned className="h-5 w-5" /> },
          ].map((p) => (
            <div key={p.name} className="card p-5 flex items-center gap-3">
              <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950/40 p-3 text-emerald-700 dark:text-emerald-300">
                {p.icon}
              </div>
              <div>
                <div className="font-semibold">{p.name}</div>
                <div className="text-xs text-slate-500">{p.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
