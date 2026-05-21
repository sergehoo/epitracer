'use client';

import Link from 'next/link';
import { useState } from 'react';
import {
  ArrowRight, Building2, FileBadge2, HandHelping, HeartHandshake,
  HeartPulse, Hospital, MessageCircle, Phone, PhoneCall,
  Plus, QrCode, ShieldCheck, Sparkles, Stethoscope,
} from 'lucide-react';

/* ============================================================ */
/* Landing INHP — inspirée strictement du mockup officiel          */
/* Palette : ciOrange #F77F00 · ciGreen #009B5A · ciDark #064E3B  */
/* ============================================================ */

export default function HomePage() {
  return (
    <>
      <OfficialBanner />
      <Hero />
      <Accompagnement />
      <PreventionEbola />
      <Parcours />
      <Fonctionnement />
      <Urgence />
      <FAQ />
      <CtaFinal />
    </>
  );
}

/* ----------------- BANDEAU INSTITUTIONNEL -----------------
   À GAUCHE : MSHPCMU + INHP
   À DROITE : Emblème CI, juste au-dessus de "Union · Discipline · Travail"
   --------------------------------------------------------- */
function OfficialBanner() {
  return (
    <section className="relative bg-white border-b border-slate-200">
      <div className="absolute inset-0 pattern-dots opacity-30" />
      <div className="relative max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        {/* GAUCHE : logos institutionnels MSHPCMU + INHP */}
        <div className="flex items-center gap-5">
          <img
            src="/logo-min-sante-2.png"
            alt="MSHPCMU"
            className="h-16 w-16 object-contain"
          />
          <div className="border-l border-slate-200 pl-5 leading-tight">
            <div className="text-[10px] uppercase tracking-widest text-ciOrange font-bold">
              Ministère
            </div>
            <div className="font-display font-black text-ciDark text-base">
              MSHPCMU
            </div>
            <div className="text-[10px] text-slate-500 max-w-xs leading-snug">
              Ministère de la Santé, de l'Hygiène Publique<br />
              et de la Couverture Maladie Universelle
            </div>
          </div>
          <img
            src="/logo-INHP.png"
            alt="Institut National d'Hygiène Publique"
            className="hidden sm:block h-12 w-auto object-contain"
          />
        </div>

        {/* DROITE : emblème CI au-dessus de la devise */}
        <div className="flex flex-col items-center text-center">
          <img
            src="/armoirie-ci-2.png"
            alt="Armoiries de la République de Côte d'Ivoire"
            className="h-20 w-20 object-contain drop-shadow-sm"
          />
          <div className="mt-1 text-[10px] uppercase tracking-widest text-ciOrange font-bold">
            République de Côte d'Ivoire
          </div>
          <div className="italic text-xs text-ciDark font-semibold">
            Union · Discipline · Travail
          </div>
        </div>
      </div>
    </section>
  );
}

/* ----------------------------- HERO ----------------------------- */
function Hero() {
  return (
    <section className="relative min-h-[90vh] pt-16 pb-24 overflow-hidden bg-gradient-to-br from-orange-50 via-white to-emerald-50">
      <div className="absolute inset-0 pattern-dots opacity-50" />
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-ciOrange/25 rounded-full blur-3xl" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-ciGreen/25 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
        <div>
          <span className="pill-dark border border-orange-100 text-ciOrange">
            <Sparkles className="h-3.5 w-3.5" /> Bienvenue en Côte d'Ivoire
          </span>

          <h1 className="mt-6 font-display text-5xl md:text-7xl font-black leading-tight text-ciDark tracking-tight">
            Votre arrivée, <span className="text-ciOrange">simplement accompagnée</span> et protégée.
          </h1>

          <p className="mt-6 text-lg text-slate-600 max-w-xl leading-8">
            Cette plateforme vous aide à préparer votre entrée sur le territoire, à recevoir les bonnes
            informations sanitaires et à bénéficier d'un accompagnement clair, humain et rassurant
            pendant votre séjour.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-4">
            <Link href="/voyageur" className="btn-orange">
              Préparer mon arrivée <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#fonctionnement" className="btn-paper">
              Comprendre le dispositif
            </a>
          </div>

          <div className="mt-10 grid grid-cols-3 gap-5 max-w-lg">
            <Stat value="21j" label="Accompagnement possible" />
            <Stat value="QR" label="Pass pratique" />
            <Stat value="24/7" label="Aide disponible" />
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-6 bg-gradient-to-br from-ciOrange/20 to-ciGreen/20 rounded-[3rem] blur-2xl" />
          <div className="relative bg-white/90 backdrop-blur-2xl rounded-[2rem] p-6 shadow-2xl border border-white">
            <div className="aspect-[16/10] w-full rounded-[1.5rem] bg-gradient-to-br from-ciDark via-emerald-800 to-emerald-600 grid place-items-center text-white relative overflow-hidden">
              <div className="absolute inset-0 pattern-dots opacity-30" />
              <div className="relative grid grid-cols-2 gap-6 p-6 w-full">
                <div className="bg-white/10 backdrop-blur rounded-2xl p-4 border border-white/20">
                  <div className="text-xs uppercase tracking-wide text-emerald-100">Pass numéro</div>
                  <div className="font-black text-lg mt-1">PASS-7F3A9K2X</div>
                </div>
                <div className="bg-white/10 backdrop-blur rounded-2xl p-4 border border-white/20">
                  <div className="text-xs uppercase tracking-wide text-emerald-100">Statut</div>
                  <div className="font-black text-lg mt-1 text-ciOrange">Accompagné</div>
                </div>
                <div className="col-span-2 bg-white text-ciDark rounded-2xl p-4 grid grid-cols-[auto,1fr] gap-3 items-center">
                  <div className="h-14 w-14 rounded-xl bg-ciDark grid place-items-center text-white">
                    <QrCode className="h-7 w-7" />
                  </div>
                  <div>
                    <div className="font-black">QR sanitaire signé</div>
                    <div className="text-xs text-slate-500">Vérifiable hors-ligne</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <p className="text-sm text-slate-500">Fiche d'accompagnement sanitaire</p>
              <h3 className="font-display text-2xl font-black text-ciDark">Pass Voyageur CI</h3>
              <p className="mt-3 text-slate-600 leading-7">
                Un document simple à présenter aux équipes sanitaires pour faciliter votre orientation
                et vous faire gagner du temps à l'arrivée.
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="rounded-2xl bg-orange-50 p-4">
                <p className="text-xs text-slate-500">Maladie suivie</p>
                <p className="font-black text-ciOrange">Ebola (MVE)</p>
              </div>
              <div className="rounded-2xl bg-emerald-50 p-4">
                <p className="text-xs text-slate-500">Surveillance</p>
                <p className="font-black text-ciGreen">21 jours</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="font-display text-3xl font-black text-ciDark">{value}</p>
      <p className="text-sm text-slate-500 mt-1">{label}</p>
    </div>
  );
}

/* ----------------------- ACCOMPAGNEMENT ---------------------- */
function Accompagnement() {
  const cards = [
    { icon: <HandHelping className="h-7 w-7" />, title: 'Accueil humain', desc: 'Des agents formés vous orientent avec calme et respect.', bg: 'bg-orange-50', border: 'border-orange-100' },
    { icon: <FileBadge2 className="h-7 w-7" />, title: 'Formalités simples', desc: 'Une fiche numérique claire pour éviter les répétitions.', bg: 'bg-white', border: 'border-slate-100 shadow-sm' },
    { icon: <MessageCircle className="h-7 w-7" />, title: 'Conseils utiles', desc: 'Des recommandations adaptées à votre situation.', bg: 'bg-emerald-50', border: 'border-emerald-100' },
    { icon: <ShieldCheck className="h-7 w-7" />, title: 'Protection discrète', desc: 'Un accompagnement sanitaire respectueux et confidentiel.', bg: 'bg-slate-50', border: 'border-slate-100' },
  ];
  return (
    <section id="accompagnement" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <h2 className="font-display text-4xl font-black text-ciDark">Un dispositif pensé pour vous accompagner</h2>
          <p className="mt-4 text-slate-600 leading-7">
            L'objectif n'est pas de vous surveiller, mais de vous aider à voyager sereinement,
            à recevoir les bonnes informations et à protéger votre santé ainsi que celle de vos proches.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-6">
          {cards.map((c) => (
            <article key={c.title} className={`p-6 rounded-3xl border ${c.bg} ${c.border} hover:-translate-y-1 transition`}>
              <div className="text-ciOrange mb-4">{c.icon}</div>
              <h3 className="font-black text-lg text-ciDark">{c.title}</h3>
              <p className="mt-2 text-sm text-slate-600 leading-6">{c.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------- PRÉVENTION EBOLA ---------------------- */
function PreventionEbola() {
  const tips = [
    { icon: <HeartPulse className="h-6 w-6" />, title: 'Lavez-vous régulièrement les mains', desc: "Avec de l'eau et du savon ou une solution hydroalcoolique." },
    { icon: <HeartHandshake className="h-6 w-6" />, title: 'Évitez les contacts à risque', desc: "En cas de doute, demandez conseil à un agent de santé." },
    { icon: <Hospital className="h-6 w-6" />, title: 'Consultez rapidement si vous ne vous sentez pas bien', desc: "Une prise en charge précoce protège mieux le voyageur et son entourage." },
  ];
  return (
    <section id="ebola" className="py-24 bg-gradient-to-br from-white via-orange-50/40 to-emerald-50/60">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <span className="pill-green">
            <ShieldCheck className="h-3.5 w-3.5" /> Prévention Ebola
          </span>
          <h2 className="mt-5 font-display text-4xl md:text-5xl font-black text-ciDark leading-tight">
            Quelques gestes simples pour voyager <span className="text-ciOrange">avec tranquillité</span>.
          </h2>
          <p className="mt-5 text-slate-600 leading-8">
            La maladie à virus Ebola peut être prévenue par des gestes simples, une information fiable
            et une réaction rapide en cas de symptômes. Les équipes sanitaires sont là pour vous guider,
            répondre à vos questions et vous accompagner sans jugement.
          </p>

          <div className="mt-8 space-y-4">
            {tips.map((t) => (
              <div key={t.title} className="flex gap-4 p-4 rounded-2xl bg-white border border-slate-100 shadow-sm">
                <div className="h-12 w-12 shrink-0 rounded-2xl bg-emerald-50 text-ciGreen grid place-items-center">{t.icon}</div>
                <div>
                  <h3 className="font-black text-ciDark">{t.title}</h3>
                  <p className="text-sm text-slate-600 mt-1 leading-6">{t.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-6 rounded-[3rem] bg-gradient-to-br from-ciOrange/20 to-ciGreen/20 blur-2xl" />
          <div className="relative rounded-[2rem] overflow-hidden shadow-2xl bg-gradient-to-br from-ciDark via-emerald-900 to-emerald-700 text-white p-10 min-h-[520px] flex flex-col justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-xs font-black backdrop-blur">
                <Stethoscope className="h-3.5 w-3.5" /> Information sanitaire
              </div>
              <h3 className="mt-6 font-display text-3xl font-black leading-tight">
                Maladie à Virus Ebola — l'essentiel à connaître
              </h3>
              <p className="mt-4 text-emerald-100 leading-7">
                Incubation jusqu'à 21 jours. Transmission par contact direct avec les fluides corporels
                d'une personne ou d'un animal infecté (chauve-souris frugivore, primates).
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <KpiPill big="21" sub="jours d'incubation" />
              <KpiPill big="7" sub="symptômes-clés" />
              <KpiPill big="3" sub="numéros d'urgence" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function KpiPill({ big, sub }: { big: string; sub: string }) {
  return (
    <div className="rounded-2xl bg-white/10 backdrop-blur border border-white/15 p-4 text-center">
      <div className="font-display text-3xl font-black text-ciOrange">{big}</div>
      <div className="text-[11px] text-emerald-100 mt-1">{sub}</div>
    </div>
  );
}

/* --------------------------- PARCOURS -------------------------- */
function Parcours() {
  const steps = [
    { n: '1. Préparer', desc: 'Remplissez vos informations avant ou à votre arrivée.', icon: <FileBadge2 className="h-7 w-7" /> },
    { n: '2. Présenter', desc: 'Votre QR code facilite votre passage et votre orientation.', icon: <QrCode className="h-7 w-7" /> },
    { n: '3. Être accompagné', desc: 'Recevez des conseils utiles durant votre séjour.', icon: <HandHelping className="h-7 w-7" /> },
  ];
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-3 gap-10">
        <div>
          <h2 className="font-display text-4xl font-black text-ciDark">Votre parcours en douceur</h2>
          <p className="mt-4 text-slate-600 leading-7">
            Chaque étape est conçue pour être simple, rapide et rassurante.
          </p>
          <Link href="/voyageur" className="btn-orange mt-8">
            Commencer <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="lg:col-span-2 grid md:grid-cols-3 gap-6">
          {steps.map((s) => (
            <article key={s.n} className="rounded-3xl overflow-hidden bg-white border border-slate-100 shadow-sm hover:-translate-y-1 transition">
              <div className="h-32 bg-gradient-to-br from-orange-50 to-emerald-50 grid place-items-center text-ciOrange">
                {s.icon}
              </div>
              <div className="p-6">
                <h3 className="font-black text-ciDark">{s.n}</h3>
                <p className="mt-2 text-sm text-slate-600 leading-6">{s.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------ FONCTIONNEMENT ----------------------- */
function Fonctionnement() {
  const steps = [
    { n: '01', t: 'Je renseigne', d: 'Quelques informations utiles pour mieux vous orienter.' },
    { n: '02', t: 'Je reçois', d: 'Une fiche avec QR code simple à présenter.' },
    { n: '03', t: 'Je suis orienté', d: 'Les agents sanitaires facilitent votre parcours.' },
    { n: '04', t: 'Je reste informé', d: 'Des conseils simples vous accompagnent si nécessaire.' },
  ];
  return (
    <section id="fonctionnement" className="py-24 bg-ciDark text-white relative overflow-hidden">
      <div className="absolute inset-0 pattern-dots opacity-10" />
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-ciOrange/20 rounded-full blur-3xl" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-ciGreen/20 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-5 py-2 text-xs font-black uppercase tracking-wide text-ciOrange">
            <Sparkles className="h-3.5 w-3.5" /> Étape par étape
          </span>
          <h2 className="mt-4 font-display text-4xl font-black">Comment ça marche ?</h2>
          <p className="mt-4 text-emerald-100/80 leading-7">
            Un parcours numérique fluide, conçu avec les équipes de l'INHP.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-6">
          {steps.map((s) => (
            <article key={s.n} className="p-6 rounded-3xl bg-white/10 border border-white/10 hover:bg-white/15 transition">
              <span className="font-display text-ciOrange font-black text-sm">{s.n}</span>
              <h3 className="font-black text-xl mt-4">{s.t}</h3>
              <p className="mt-3 text-emerald-100/80 leading-6">{s.d}</p>
            </article>
          ))}
        </div>

        <div className="mt-12 grid md:grid-cols-3 gap-4">
          {['Aéroport FHB Abidjan', "Port Autonome d'Abidjan", 'Port de San-Pédro',
            'Frontière de Pôgô', 'Frontière de Niablé', 'Aéroport de Yamoussoukro',
          ].map((name) => (
            <div key={name} className="rounded-2xl bg-white/5 border border-white/10 p-4 flex items-center gap-3">
              <Building2 className="h-5 w-5 text-ciOrange" />
              <span className="text-sm font-semibold">{name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------- URGENCE -------------------------- */
function Urgence() {
  const phones = [
    { label: 'SAMU National', sub: 'Appel gratuit', n: '185' },
    { label: 'Allô Santé', sub: 'MSHPCMU (Ministère de la Santé)', n: '143' },
    { label: 'Police / Secours', sub: 'Centre national', n: '101' },
  ];
  return (
    <section id="urgence" className="py-24 bg-gradient-to-br from-ciOrange to-red-600 text-white">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/20 rounded-full font-black uppercase text-xs tracking-wide mb-5">
            <Phone className="h-3.5 w-3.5" /> Assistance sanitaire
          </span>
          <h2 className="font-display text-4xl md:text-5xl font-black leading-tight">
            Un doute, un symptôme, une question ?
          </h2>
          <p className="mt-5 text-white/90 text-lg leading-8">
            Vous n'êtes pas seul. Les services de santé sont disponibles pour vous écouter,
            vous rassurer et vous orienter rapidement vers la meilleure prise en charge.
          </p>
          <Link href="/assistance" className="mt-7 inline-flex items-center gap-2 rounded-2xl bg-white text-ciDark px-7 py-4 font-black shadow-xl hover:-translate-y-0.5 transition">
            Voir tous les conseils <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="bg-white text-slate-900 rounded-[2rem] p-8 shadow-2xl">
          <h3 className="font-display font-black text-2xl mb-6 text-ciDark">Contacts utiles</h3>
          <ul className="space-y-4">
            {phones.map((p, i) => (
              <li key={p.n} className={`flex items-center justify-between ${i < phones.length - 1 ? 'border-b pb-4' : ''}`}>
                <div>
                  <div className="font-bold text-ciDark">{p.label}</div>
                  <div className="text-xs text-slate-500">{p.sub}</div>
                </div>
                <a href={`tel:${p.n}`} className="inline-flex items-center gap-2 font-black text-2xl text-ciOrange hover:text-orange-600">
                  <PhoneCall className="h-5 w-5" />{p.n}
                </a>
              </li>
            ))}
          </ul>
          <Link href="/voyageur" className="mt-8 block text-center px-6 py-4 rounded-2xl bg-ciDark text-white font-black hover:bg-emerald-950 transition">
            Demander une orientation
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------ FAQ ---------------------------- */
const FAQS = [
  {
    q: "Pourquoi me demande-t-on ces informations ?",
    a: "Ces informations permettent aux équipes sanitaires de mieux vous orienter, de vous donner des conseils adaptés et de faciliter votre passage aux points d'entrée.",
  },
  {
    q: "Mes données sont-elles confidentielles ?",
    a: "Oui. Vos informations sont protégées (signature cryptographique Ed25519, accès strict RBAC) et utilisées uniquement dans le cadre de l'accompagnement sanitaire et de la protection de la santé publique.",
  },
  {
    q: "Que se passe-t-il si je ne me sens pas bien ?",
    a: "Vous pouvez contacter les services sanitaires. Un agent vous orientera calmement vers la conduite à tenir et, si nécessaire, vers le centre de santé approprié.",
  },
  {
    q: "Est-ce que cela va ralentir mon arrivée ?",
    a: "Au contraire, le pré-enregistrement permet souvent de gagner du temps, car votre fiche est déjà prête et le QR code facilite votre orientation.",
  },
];

function FAQ() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="py-24 bg-slate-50">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h2 className="font-display text-4xl font-black text-ciDark">Questions fréquentes</h2>
          <p className="mt-3 text-slate-600">Les réponses aux interrogations les plus courantes des voyageurs.</p>
        </div>
        <div className="space-y-4">
          {FAQS.map((f, i) => {
            const isOpen = open === i;
            return (
              <article key={i} className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="w-full flex justify-between items-center gap-4 text-left font-black text-ciDark"
                >
                  <span>{f.q}</span>
                  <span className={`text-ciOrange transition-transform ${isOpen ? 'rotate-45' : ''}`}>
                    <Plus className="h-5 w-5" />
                  </span>
                </button>
                {isOpen && (
                  <p className="mt-4 text-slate-600 leading-7 animate-fade-up">{f.a}</p>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* -------------------------- CTA FINAL -------------------------- */
function CtaFinal() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <h2 className="font-display text-4xl md:text-5xl font-black text-ciDark">
          Préparez votre arrivée <span className="text-ciOrange">en toute sérénité</span>
        </h2>
        <p className="mt-4 text-slate-600 leading-7 max-w-2xl mx-auto">
          Quelques minutes suffisent pour recevoir votre fiche sanitaire et bénéficier d'un
          accompagnement simple, rassurant et respectueux.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/voyageur" className="btn-orange">
            Préparer mon arrivée <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/verifier" className="btn-paper">
            Vérifier mon pass
          </Link>
        </div>
      </div>
    </section>
  );
}
