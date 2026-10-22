import Link from 'next/link';
import {
  ArrowRight, Building2, FileBadge2, HandHelping,
  HeartPulse, Megaphone, MessageCircle, Phone, PhoneCall,
  QrCode, ShieldCheck, Sparkles, Stethoscope,
} from 'lucide-react';
import { DiseaseCard } from '@/components/public/DiseaseCard';
import { HomeFaq } from '@/components/public/HomeFaq';
import { NoticeCard } from '@/components/public/NoticeCard';
import { ALERT_LEVEL_ORDER, fetchPublicDiseases, fetchPublicNotices } from '@/lib/portal';
import type { PublicDisease, PublicNotice } from '@/types/portal';

// Contenus publiés par les autorités : régénérés toutes les 5 minutes.
export const revalidate = 300;

/* ============================================================ */
/* Landing INHP — inspirée strictement du mockup officiel          */
/* Palette : ciOrange #F77F00 · ciGreen #009B5A · ciDark #064E3B  */
/* ============================================================ */

export default async function HomePage() {
  const [diseases, notices] = await Promise.all([
    fetchPublicDiseases('?active=true'),
    fetchPublicNotices(),
  ]);
  return (
    <>
      <OfficialBanner />
      <Hero />
      <Accompagnement />
      <VeilleSanitaire diseases={diseases} notices={notices} />
      <Parcours />
      <Fonctionnement />
      <Urgence />
      <HomeFaq />
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
          <div className="border-l border-slate-200 pl-2 leading-tight">

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
            EpiTrace est le dispositif national d'information, de prévention et d'accompagnement
            sanitaire des voyageurs, porté par le MSHPCMU et l'INHP. Il vous aide à préparer votre
            entrée sur le territoire, à connaître les maladies sous surveillance et à bénéficier d'un
            accompagnement clair, humain et rassurant pendant votre séjour.
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
            <Stat value="1" label="Fiche unique pour votre séjour" />
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
                <p className="text-xs text-slate-500">Maladies suivies</p>
                <p className="font-black text-ciOrange">Selon la situation</p>
              </div>
              <div className="rounded-2xl bg-emerald-50 p-4">
                <p className="text-xs text-slate-500">Suivi</p>
                <p className="font-black text-ciGreen">Selon le protocole</p>
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

/* ------------------- MALADIES SOUS SURVEILLANCE ------------------- */
/* Contenus publiés par les administrateurs habilités (API /public/).    */
function VeilleSanitaire({ diseases, notices }: { diseases: PublicDisease[]; notices: PublicNotice[] }) {
  const alerts = notices
    .filter((n) => n.kind === 'alert')
    .sort((a, b) => ALERT_LEVEL_ORDER.indexOf(a.alert_level) - ALERT_LEVEL_ORDER.indexOf(b.alert_level));
  const recommendations = notices.filter((n) => n.kind === 'recommendation');

  return (
    <section
      id="maladies"
      aria-labelledby="maladies-title"
      className="py-24 bg-gradient-to-br from-white via-orange-50/40 to-emerald-50/60"
    >
      {/* Ancre historique conservée pour les anciens liens /#ebola */}
      <span id="ebola" className="sr-only" aria-hidden="true" />
      <div className="max-w-7xl mx-auto px-6">
        <div className="max-w-3xl">
          <span className="pill-green">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Maladies sous surveillance
          </span>
          <h2 id="maladies-title" className="mt-5 font-display text-4xl md:text-5xl font-black text-ciDark leading-tight">
            S'informer pour voyager <span className="text-ciOrange">en toute tranquillité</span>.
          </h2>
          <p className="mt-5 text-slate-600 leading-8">
            Les autorités sanitaires ivoiriennes publient ici les alertes en cours, les maladies
            actuellement surveillées et les recommandations utiles aux voyageurs. Ces informations
            sont validées par le MSHPCMU et l'INHP.
          </p>
        </div>

        {alerts.length > 0 && (
          <div className="mt-12" role="region" aria-labelledby="alertes-title">
            <h3 id="alertes-title" className="font-display text-2xl font-black text-ciDark inline-flex items-center gap-2">
              <Megaphone className="h-6 w-6 text-ciOrange" aria-hidden="true" /> Alertes sanitaires en cours
            </h3>
            <div className="mt-6 grid gap-6 md:grid-cols-2">
              {alerts.slice(0, 4).map((n) => <NoticeCard key={n.uuid} notice={n} />)}
            </div>
          </div>
        )}

        <div className="mt-12">
          <h3 className="font-display text-2xl font-black text-ciDark">Maladies actuellement surveillées</h3>
          {diseases.length > 0 ? (
            <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {diseases.slice(0, 6).map((d) => <DiseaseCard key={d.slug} disease={d} />)}
            </div>
          ) : (
            <p className="mt-6 rounded-2xl border border-slate-100 bg-white p-6 text-slate-600">
              Les fiches d'information sont publiées par les autorités sanitaires au fil de la
              situation. En cas de doute ou de symptôme, contactez le <a href="tel:143" className="font-bold text-ciOrange">143</a>.
            </p>
          )}
          <Link href="/maladies" className="btn-paper mt-8 inline-flex">
            Toutes les fiches maladies <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        {recommendations.length > 0 && (
          <div className="mt-12" role="region" aria-labelledby="recos-title">
            <h3 id="recos-title" className="font-display text-2xl font-black text-ciDark inline-flex items-center gap-2">
              <Stethoscope className="h-6 w-6 text-ciGreen" aria-hidden="true" /> Recommandations aux voyageurs
            </h3>
            <div className="mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {recommendations.slice(0, 6).map((n) => <NoticeCard key={n.uuid} notice={n} />)}
            </div>
          </div>
        )}
      </div>
    </section>
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
    {
      n: '01',
      icon: <FileBadge2 className="h-6 w-6" />,
      title: 'Je remplis ma fiche en ligne',
      duration: '≈ 5 minutes',
      desc: "Avant ou pendant votre voyage, renseignez vos informations d'identité, votre itinéraire, votre hébergement en Côte d'Ivoire et votre contact d'urgence. Aucun document papier à imprimer.",
      action: 'Identité · Voyage · Hébergement · Contact urgence',
    },
    {
      n: '02',
      icon: <QrCode className="h-6 w-6" />,
      title: 'Je reçois mon pass sanitaire',
      duration: 'Immédiat',
      desc: "Un QR code signé cryptographiquement et une fiche officielle PDF vous sont délivrés instantanément. Téléchargeables, valables sur smartphone hors-ligne, sécurisés par signature Ed25519.",
      action: 'QR code + PDF officiel INHP',
    },
    {
      n: '03',
      icon: <ShieldCheck className="h-6 w-6" />,
      title: 'Je passe le contrôle sanitaire',
      duration: '< 30 secondes',
      desc: "À l'arrivée au point d'entrée (aéroport FHB, ports, frontières terrestres), un agent INHP scanne votre QR. Vérification d'authenticité instantanée, orientation rapide vers le poste sanitaire si nécessaire.",
      action: 'Scan QR · Vérification signature · Orientation',
    },
    {
      n: '04',
      icon: <HeartPulse className="h-6 w-6" />,
      title: 'Je suis accompagné si nécessaire',
      duration: 'Suivi adapté',
      desc: "Si votre situation le justifie, un suivi est ouvert pour la ou les maladies concernées, pour la durée prévue par leur protocole (21 jours pour Ebola, par exemple). Un rappel WhatsApp / SMS vous invite chaque jour à confirmer votre état de santé ; en cas de doute, appelez le 143 (gratuit).",
      action: 'Check-in quotidien · Ligne 143 · Conseils personnalisés',
    },
  ];

  return (
    <section id="fonctionnement" className="py-24 bg-ciDark text-white relative overflow-hidden">
      <div className="absolute inset-0 pattern-dots opacity-10" />
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-ciOrange/20 rounded-full blur-3xl" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-ciGreen/20 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-5 py-2 text-xs font-black uppercase tracking-wide text-ciOrange">
            <Sparkles className="h-3.5 w-3.5" /> Comment ça fonctionne
          </span>
          <h2 className="mt-4 font-display text-4xl font-black">
            Votre parcours en <span className="text-ciOrange">4 étapes</span>
          </h2>
          <p className="mt-4 text-emerald-100/80 leading-7">
            Un dispositif numérique simple et sécurisé, conçu avec l'INHP pour vous
            accompagner avant, pendant et après votre arrivée en Côte d'Ivoire.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, idx) => (
            <article
              key={s.n}
              className="relative p-6 rounded-3xl bg-white/10 border border-white/10 hover:bg-white/15 hover:-translate-y-1 transition flex flex-col"
            >
              {/* En-tête : numéro + icône */}
              <div className="flex items-center justify-between">
                <span className="font-display text-ciOrange font-black text-2xl">{s.n}</span>
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-ciOrange/20 text-ciOrange">
                  {s.icon}
                </span>
              </div>

              {/* Durée / délai */}
              <span className="mt-4 inline-flex items-center self-start gap-1.5 rounded-full bg-ciGreen/20 px-3 py-1 text-[11px] font-bold text-emerald-200 uppercase tracking-wide">
                {s.duration}
              </span>

              {/* Titre + description */}
              <h3 className="font-black text-xl mt-3 leading-snug">{s.title}</h3>
              <p className="mt-3 text-sm text-emerald-100/80 leading-6 flex-1">
                {s.desc}
              </p>

              {/* Détail / mots-clés */}
              <div className="mt-5 pt-4 border-t border-white/10">
                <p className="text-[11px] font-semibold text-ciOrange/90 leading-relaxed">
                  {s.action}
                </p>
              </div>

              {/* Flèche de progression entre cartes (desktop) */}
              {idx < steps.length - 1 && (
                <ArrowRight className="hidden lg:block absolute top-1/2 -right-4 h-5 w-5 text-ciOrange/50 -translate-y-1/2" />
              )}
            </article>
          ))}
        </div>

        {/* CTA + points d'entrée */}
        <div className="mt-12 text-center">
          <Link href="/voyageur" className="btn-orange inline-flex">
            Commencer ma fiche maintenant <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="mt-10 grid md:grid-cols-3 gap-4">
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

/* -------------------------- CTA FINAL -------------------------- */
function CtaFinal() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <h2 className="font-display text-4xl md:text-5xl font-black text-ciDark">
          Préparez votre arrivée <span className="text-ciOrange">en toute sérénité</span>
        </h2>
        <p className="mt-4 text-slate-600 leading-7 max-w-2xl mx-auto">
          Quelques minutes suffisent pour recevoir votre pass sanitaire, connaître les mesures de
          prévention utiles et bénéficier d'un accompagnement simple, rassurant et respectueux.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/voyageur" className="btn-orange">
            Préparer mon arrivée <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/pass" className="btn-paper">
            Consulter mon pass
          </Link>
        </div>
      </div>
    </section>
  );
}
