'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';

const FAQS = [
  {
    q: 'Pourquoi me demande-t-on ces informations ?',
    a: "Ces informations permettent aux équipes sanitaires de mieux vous orienter, de vous donner des conseils adaptés aux maladies sous surveillance et de faciliter votre passage aux points d'entrée.",
  },
  {
    q: 'Quelles maladies sont concernées ?',
    a: "Uniquement les maladies placées sous surveillance par les autorités sanitaires ivoiriennes. La liste évolue selon la situation épidémiologique et est consultable à tout moment dans la rubrique « Maladies sous surveillance ».",
  },
  {
    q: 'Puis-je être suivi pour plusieurs maladies ?',
    a: "Oui. Votre fiche est unique : si votre situation le justifie, un accompagnement est ouvert pour chaque maladie concernée, avec la durée prévue par son protocole, sans que vous ayez à vous réenregistrer.",
  },
  {
    q: 'Mes données sont-elles confidentielles ?',
    a: "Oui. Vos informations sont protégées (signature cryptographique Ed25519, accès strict RBAC) et utilisées uniquement dans le cadre de l'accompagnement sanitaire et de la protection de la santé publique.",
  },
  {
    q: 'Que se passe-t-il si je ne me sens pas bien ?',
    a: 'Vous pouvez contacter les services sanitaires. Un agent vous orientera calmement vers la conduite à tenir et, si nécessaire, vers le centre de santé approprié.',
  },
  {
    q: 'Est-ce que cela va ralentir mon arrivée ?',
    a: 'Au contraire, le pré-enregistrement permet souvent de gagner du temps, car votre fiche est déjà prête et le QR code facilite votre orientation.',
  },
];

export function HomeFaq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="py-24 bg-slate-50" aria-labelledby="faq-title">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h2 id="faq-title" className="font-display text-4xl font-black text-ciDark">Questions fréquentes</h2>
          <p className="mt-3 text-slate-600">Les réponses aux interrogations les plus courantes des voyageurs.</p>
        </div>
        <div className="space-y-4">
          {FAQS.map((f, i) => {
            const isOpen = open === i;
            return (
              <article key={f.q} className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
                <h3>
                  <button
                    onClick={() => setOpen(isOpen ? null : i)}
                    aria-expanded={isOpen}
                    aria-controls={`faq-${i}`}
                    className="w-full flex justify-between items-center gap-4 text-left font-black text-ciDark"
                  >
                    <span>{f.q}</span>
                    <span className={`text-ciOrange transition-transform ${isOpen ? 'rotate-45' : ''}`} aria-hidden="true">
                      <Plus className="h-5 w-5" />
                    </span>
                  </button>
                </h3>
                {isOpen && (
                  <p id={`faq-${i}`} className="mt-4 text-slate-600 leading-7 animate-fade-up">{f.a}</p>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
