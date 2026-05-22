'use client';

/**
 * /dashboard/parametres — Page de paramètres administratifs.
 *
 * Regroupe les réglages utilisateur (préférences, thème) et les infos
 * système non confidentielles (env, version, clé publique VAPID).
 */

import { useEffect, useState } from 'react';
import {
  Bell, Globe2, Info, KeyRound, Moon, Palette, Server, Sun, User,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { api, API_URL } from '@/lib/api';

interface VapidResp { public_key: string }

export default function ParametresPage() {
  const { theme, setTheme, systemTheme } = useTheme();
  const [vapid, setVapid] = useState<string>('');
  const [me, setMe] = useState<{ email?: string; role?: string } | null>(null);

  useEffect(() => {
    api.get<VapidResp>('/public/push/public-key/').then((r) => setVapid(r.data.public_key)).catch(() => undefined);
    api.get<{ email: string; role: string }>('/auth/me/').then((r) => setMe(r.data)).catch(() => undefined);
  }, []);

  const effectiveTheme = theme === 'system' ? systemTheme : theme;

  return (
    <div className="space-y-6 max-w-5xl">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Réglages
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Paramètres
        </h1>
      </header>

      {/* ============ Compte ============ */}
      <Section icon={<User className="h-5 w-5" />} title="Mon compte">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Adresse e-mail" value={me?.email || '—'} />
          <Field label="Rôle" value={me?.role || '—'} />
        </div>
        <p className="text-xs text-slate-500 mt-3">
          Pour changer votre mot de passe ou activer la double authentification (MFA),
          contactez votre administrateur national.
        </p>
      </Section>

      {/* ============ Apparence ============ */}
      <Section icon={<Palette className="h-5 w-5" />} title="Apparence">
        <div className="flex flex-wrap gap-2">
          <ThemeOption value="light" current={theme} onChange={setTheme} icon={<Sun className="h-4 w-4" />} label="Clair" />
          <ThemeOption value="dark" current={theme} onChange={setTheme} icon={<Moon className="h-4 w-4" />} label="Sombre" />
          <ThemeOption value="system" current={theme} onChange={setTheme} icon={<Globe2 className="h-4 w-4" />} label="Système" />
        </div>
        <p className="text-xs text-slate-500 mt-3">
          Thème courant : <strong>{effectiveTheme || 'inconnu'}</strong>.
          Le mode "Système" suit automatiquement les préférences de votre OS.
        </p>
      </Section>

      {/* ============ Notifications ============ */}
      <Section icon={<Bell className="h-5 w-5" />} title="Notifications">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Les agents reçoivent les alertes critiques en temps réel dans l'interface admin
          (WebSocket) et par email pour les événements majeurs. Configuration centrale
          assurée par l'administrateur national.
        </p>
      </Section>

      {/* ============ Système & API ============ */}
      <Section icon={<Server className="h-5 w-5" />} title="Système & API">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="URL API" value={API_URL || '—'} mono />
          <Field label="Environnement" value={process.env.NODE_ENV || 'production'} />
        </div>
      </Section>

      {/* ============ VAPID (Web Push) ============ */}
      {vapid && (
        <Section icon={<KeyRound className="h-5 w-5" />} title="Clé publique Web Push (VAPID)">
          <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">
            Clé exposée à la PWA voyageur pour s'abonner aux notifications push.
            Information publique — peut être partagée librement.
          </p>
          <div className="card p-3 bg-slate-50 dark:bg-slate-900 font-mono text-[11px] break-all">
            {vapid}
          </div>
        </Section>
      )}

      <div className="card p-4 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 flex items-start gap-2">
        <Info className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Pour les paramètres avancés (gestion utilisateurs, RBAC, intégrations Twilio,
          envois SMS/WhatsApp, génération de clés cryptographiques) → contactez l'administrateur
          système ou utilisez l'interface Django Admin sécurisée.
        </p>
      </div>
    </div>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <section className="card p-5">
      <header className="flex items-center gap-2 mb-3 text-emerald-700 dark:text-emerald-300">
        {icon}
        <h2 className="font-display font-bold text-ciDark dark:text-emerald-100">{title}</h2>
      </header>
      {children}
    </section>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-1">{label}</div>
      <div className={`text-sm ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  );
}

function ThemeOption({
  value, current, onChange, icon, label,
}: {
  value: string; current?: string;
  onChange: (v: string) => void;
  icon: React.ReactNode; label: string;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onChange(value)}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border transition ${
        active
          ? 'bg-emerald-600 text-white border-emerald-600 shadow'
          : 'bg-white border-slate-200 hover:border-emerald-500'
      }`}
    >
      {icon}
      <span className="text-sm font-semibold">{label}</span>
    </button>
  );
}
