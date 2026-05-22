'use client';

/**
 * Politique de confidentialité — version voyageur.
 *
 * Cette page est volontairement courte, lisible, en français simple.
 * Elle correspond à la version CONSENT_VERSION exposée côté front.
 * Toute modification substantielle doit s'accompagner d'un bump de version
 * dans `lib/companion.ts` pour que les nouveaux consentements soient
 * rattachés à la nouvelle version.
 */

import { Section } from '@/components/ui/Section';
import { ShieldCheck, Eye, Database, Trash2, MapPin } from 'lucide-react';
import { CONSENT_VERSION } from '@/lib/companion';

export default function ConfidentialitePage() {
  return (
    <Section
      eyebrow="Vos données, votre confiance"
      title="Politique de confidentialité"
      description={`Version ${CONSENT_VERSION} — applicable au moment de votre consentement.`}
    >
      <div className="prose dark:prose-invert max-w-3xl mx-auto space-y-6 text-sm">
        <Block
          icon={<ShieldCheck className="h-5 w-5 text-emerald-600" />}
          title="Pourquoi collectons-nous ces informations ?"
        >
          Vos données nous aident à vous accompagner durant votre séjour sur le
          territoire ivoirien et à mieux réagir si vous avez besoin d'assistance.
          Elles sont traitées par l'Institut National d'Hygiène Publique (INHP)
          et le Ministère de la Santé, de l'Hygiène Publique et de la Couverture
          Maladie Universelle (MSHPCMU).
        </Block>

        <Block
          icon={<Database className="h-5 w-5 text-emerald-600" />}
          title="Quelles données collectons-nous ?"
        >
          Au moment de votre enregistrement : nom, contact, voyage, adresse de
          résidence en Côte d'Ivoire, document de voyage.<br />
          Pendant votre séjour : vos check-ins quotidiens (état de santé) et,
          si vous l'autorisez, votre position au moment d'un check-in ou d'une
          demande d'aide.
        </Block>

        <Block
          icon={<MapPin className="h-5 w-5 text-emerald-600" />}
          title="Position géographique — consentement explicite"
        >
          Votre position n'est <strong>jamais</strong> collectée silencieusement.
          Elle est récupérée uniquement après votre accord explicite (case à
          cocher dans votre espace de suivi), et uniquement au moment :
          <ul className="mt-2 list-disc list-inside">
            <li>d'un check-in que vous validez vous-même ;</li>
            <li>d'une demande d'aide que vous initiez ;</li>
            <li>d'une action volontaire « Partager ma position ».</li>
          </ul>
          Vous pouvez retirer ce consentement à tout moment depuis votre espace.
        </Block>

        <Block
          icon={<Eye className="h-5 w-5 text-emerald-600" />}
          title="Qui peut voir vos données ?"
        >
          Vos données ne sont consultables que par des agents habilités :
          INHP national, équipes des districts sanitaires, équipes d'urgence et
          agents terrain affectés à votre suivi. Chaque consultation est
          enregistrée dans un journal d'accès auditable.
        </Block>

        <Block
          icon={<Trash2 className="h-5 w-5 text-emerald-600" />}
          title="Combien de temps gardons-nous vos données ?"
        >
          Les données nécessaires à l'investigation épidémiologique sont
          conservées selon les obligations légales applicables aux registres
          sanitaires nationaux. À la fin de votre période d'accompagnement, vous
          pouvez nous contacter à <a className="underline" href="mailto:info@destinationci.com">info@destinationci.com</a> pour
          exercer vos droits d'accès, de rectification ou de suppression.
        </Block>

        <div className="mt-10 p-4 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-500">
          Cette plateforme est conforme à la loi ivoirienne n° 2013-450 du
          19 juin 2013 relative à la protection des données à caractère
          personnel. Pour toute question, contactez le Délégué à la Protection
          des Données via <a className="underline" href="mailto:info@destinationci.com">info@destinationci.com</a>.
        </div>
      </div>
    </Section>
  );
}

function Block({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <section className="card p-5">
      <div className="flex items-center gap-2 font-display font-bold text-ciDark dark:text-emerald-200">
        {icon}
        {title}
      </div>
      <div className="mt-2 text-slate-700 dark:text-slate-200 leading-7">{children}</div>
    </section>
  );
}
