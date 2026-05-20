import { Section } from '@/components/ui/Section';
import { Mail, PhoneCall, ShieldAlert, Stethoscope } from 'lucide-react';

export const metadata = { title: 'Assistance & Numéros d\'urgence' };

export default function AssistancePage() {
  return (
    <>
      <Section
        eyebrow="Notice sanitaire individuelle"
        title="Maladie à Virus Ebola (MVE) — Informations & Assistance"
        description="Document officiel INHP — Surveillance des voyageurs entrant sur le territoire ivoirien."
      >
        <div className="grid lg:grid-cols-3 gap-6">
          <article className="card p-6 lg:col-span-2 space-y-4 text-sm leading-relaxed">
            <h3 className="font-display text-xl font-bold">Qu'est-ce que la Maladie à Virus Ebola ?</h3>
            <p className="text-slate-700 dark:text-slate-200">
              La maladie à virus Ebola (MVE) est une infection d'une extrême gravité provoquée par
              le virus Ebola. Elle se caractérise par l'apparition brutale d'une <strong>forte fièvre</strong>,
              d'une <strong>fatigue généralisée intense</strong>, de douleurs musculaires, articulaires
              et de maux de tête. Ces symptômes initiaux sont rapidement suivis de maux de gorge,
              de vomissements, de diarrhée profuse, d'éruptions cutanées, d'insuffisance rénale ou
              hépatique et, dans certains cas graves, d'hémorragies internes et externes spontanées.
              <br /><br />
              <strong>La durée d'incubation maximale est de 21 jours.</strong>
            </p>

            <h3 className="font-display text-xl font-bold pt-2">Comment se transmet le virus ?</h3>
            <p className="text-slate-700 dark:text-slate-200">
              Le réservoir naturel est la chauve-souris frugivore. La transmission s'effectue selon
              deux axes : <em>animal à homme</em> (contact direct avec sang, fluides corporels,
              organes, sécrétions d'animaux sauvages — singes, chauves-souris, antilopes de forêt),
              et <em>personne à personne</em> (contact étroit avec sang, vomissures, urine, salive,
              sperme, matériel médical contaminé, literie, vêtements).
            </p>

            <h3 className="font-display text-xl font-bold pt-2">Mesures de prévention obligatoires</h3>
            <ul className="space-y-2 text-slate-700 dark:text-slate-200 list-disc pl-5">
              <li><strong>Hygiène des mains</strong> : lavage fréquent à l'eau courante et au savon, ou solution hydroalcoolique.</li>
              <li><strong>Distanciation sanitaire</strong> : éviter tout contact direct avec personne suspecte ou fébrile.</li>
              <li><strong>Sécurité funéraire</strong> : ne pas participer à des rites de lavage mortuaire traditionnel ou manipuler des dépouilles inconnues. Alerter les services de santé.</li>
              <li><strong>Interdiction alimentaire</strong> : s'abstenir de manipuler ou consommer de la viande de brousse / carcasses animales.</li>
            </ul>

            <div className="mt-6 rounded-xl border-l-4 border-rose-500 bg-rose-50/70 dark:bg-rose-950/30 p-4">
              <div className="flex items-center gap-2 font-semibold text-rose-700 dark:text-rose-300">
                <ShieldAlert className="h-5 w-5" />
                En cas de symptômes évocateurs (fièvre, maux de tête, saignement)
              </div>
              <p className="text-sm mt-2 text-slate-700 dark:text-slate-200">
                Rendez-vous immédiatement dans le centre de santé le plus proche
                ou contactez un des numéros d'urgence indiqués ci-contre. Ne quittez pas votre
                lieu de confinement sans consigne explicite des services sanitaires.
              </p>
            </div>
          </article>

          <aside className="space-y-4">
            <div className="card p-5">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">Numéros d'urgence</div>
              <ul className="mt-3 space-y-3">
                <li className="flex items-center justify-between rounded-xl bg-rose-50 dark:bg-rose-950/30 px-3 py-3">
                  <div>
                    <div className="text-sm font-semibold">SAMU National</div>
                    <div className="text-xs text-slate-500">Appel gratuit</div>
                  </div>
                  <a href="tel:185" className="inline-flex items-center gap-2 font-bold text-rose-700">
                    <PhoneCall className="h-4 w-4" /> 185
                  </a>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-emerald-50 dark:bg-emerald-950/30 px-3 py-3">
                  <div>
                    <div className="text-sm font-semibold">Allô Santé</div>
                    <div className="text-xs text-slate-500">Ministère de la Santé</div>
                  </div>
                  <a href="tel:143" className="inline-flex items-center gap-2 font-bold text-emerald-700">
                    <PhoneCall className="h-4 w-4" /> 143
                  </a>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-amber-50 dark:bg-amber-950/30 px-3 py-3">
                  <div>
                    <div className="text-sm font-semibold">Secours</div>
                    <div className="text-xs text-slate-500">Police · Pompiers</div>
                  </div>
                  <a href="tel:101" className="inline-flex items-center gap-2 font-bold text-amber-700">
                    <PhoneCall className="h-4 w-4" /> 101
                  </a>
                </li>
              </ul>
            </div>

            <div className="card p-5">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Stethoscope className="h-4 w-4 text-emerald-600" />
                INHP — Institut National d'Hygiène Publique
              </div>
              <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Tél : <a className="underline" href="tel:0027212535 10">27 21 25 35 10</a> · <a className="underline" href="tel:0027212597 46">27 21 25 97 46</a>
              </div>
              <div className="mt-1 text-sm">
                <Mail className="inline h-4 w-4 mr-1 text-emerald-600" />
                <a className="underline" href="mailto:episurvinhp@gmail.com">episurvinhp@gmail.com</a>
              </div>
            </div>
          </aside>
        </div>
      </Section>
    </>
  );
}
