'use client';

/**
 * Contenus publics — alertes sanitaires et recommandations aux voyageurs
 * affichées sur le portail. Cycle : brouillon → publication → archivage.
 * Seules les annonces publiées et dans leur période de validité sont visibles.
 */

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Archive, Megaphone, Plus, Send, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { ALERT_LEVEL_ORDER, ALERT_LEVEL_STYLE } from '@/lib/portal';
import type { PublicAlertLevel } from '@/types/portal';

interface Notice {
  uuid: string; kind: 'alert' | 'recommendation'; title: string; summary: string; body: string;
  alert_level: PublicAlertLevel; disease: string | null; countries: string[];
  status: 'draft' | 'published' | 'archived'; valid_from: string; valid_until: string | null;
  published_at: string | null; published_by_email: string | null;
}
interface Option { code: string; name: string }

const STATUS_BADGE: Record<Notice['status'], string> = {
  draft: 'badge-moderate', published: 'badge-low', archived: 'badge-high',
};
const STATUS_LABEL: Record<Notice['status'], string> = {
  draft: 'Brouillon', published: 'Publiée', archived: 'Archivée',
};
const EMPTY = {
  kind: 'alert' as Notice['kind'], title: '', summary: '', body: '',
  alert_level: 'moderate' as PublicAlertLevel, disease: '', countries: [] as string[],
  valid_until: '',
};
const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');

export default function ContenusPublicsPage() {
  const [items, setItems] = useState<Notice[]>([]);
  const [diseases, setDiseases] = useState<Option[]>([]);
  const [countries, setCountries] = useState<Option[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState<typeof EMPTY | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api.get('/portal/notices/?page_size=100')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);

  useEffect(() => {
    load();
    api.get('/diseases/?page_size=100').then((r) => setDiseases(r.data.results || r.data)).catch(() => undefined);
    api.get('/geo/countries/?page_size=300').then((r) => setCountries(r.data.results || r.data)).catch(() => undefined);
  }, [load]);

  const action = async (n: Notice, verb: 'publish' | 'archive') => {
    try {
      await api.post(`/portal/notices/${n.uuid}/${verb}/`);
      toast.success(verb === 'publish' ? 'Annonce publiée.' : 'Annonce archivée.');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    try {
      await api.post('/portal/notices/', {
        ...form,
        disease: form.disease || null,
        valid_until: form.valid_until ? new Date(form.valid_until).toISOString() : null,
      });
      toast.success('Brouillon enregistré. Publiez-le pour le rendre visible.');
      setForm(null);
      load();
    } catch (e2) {
      toast.error(extractApiError(e2));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Contenus publics</h1>
          <p className="text-sm text-slate-500 mt-1">
            Alertes sanitaires et recommandations aux voyageurs affichées sur le portail public.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setForm({ ...EMPTY })}>
          <Plus className="h-4 w-4" /> Nouvelle annonce
        </button>
      </div>
      {err && <div className="card p-4 text-rose-600 text-sm">{err}</div>}

      {form && (
        <form onSubmit={submit} className="card p-5 space-y-4" aria-label="Nouvelle annonce">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold">Nouvelle annonce (brouillon)</h2>
            <button type="button" className="btn-ghost" onClick={() => setForm(null)} aria-label="Fermer">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid md:grid-cols-4 gap-3">
            <label className="text-sm">Type
              <select className="select mt-1" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Notice['kind'] })}>
                <option value="alert">Alerte sanitaire</option>
                <option value="recommendation">Recommandation aux voyageurs</option>
              </select>
            </label>
            <label className="text-sm">Niveau d&apos;alerte
              <select className="select mt-1" value={form.alert_level} onChange={(e) => setForm({ ...form, alert_level: e.target.value as PublicAlertLevel })}>
                {ALERT_LEVEL_ORDER.map((l) => <option key={l} value={l}>{ALERT_LEVEL_STYLE[l].label}</option>)}
              </select>
            </label>
            <label className="text-sm">Maladie (optionnel)
              <select className="select mt-1" value={form.disease} onChange={(e) => setForm({ ...form, disease: e.target.value })}>
                <option value="">—</option>
                {diseases.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
              </select>
            </label>
            <label className="text-sm">Visible jusqu&apos;au (optionnel)
              <input type="date" className="input mt-1" value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
            </label>
          </div>
          <label className="text-sm block">Titre
            <input className="input mt-1" required maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </label>
          <label className="text-sm block">Résumé
            <input className="input mt-1" maxLength={300} value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
          </label>
          <label className="text-sm block">Contenu
            <textarea className="textarea mt-1" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </label>
          <label className="text-sm block">Pays concernés (Ctrl/Cmd + clic pour plusieurs)
            <select
              multiple
              className="select mt-1 h-32"
              value={form.countries}
              onChange={(e) => setForm({ ...form, countries: Array.from(e.target.selectedOptions).map((o) => o.value) })}
            >
              {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
          </label>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setForm(null)}>Annuler</button>
            <button type="submit" className="btn-primary" disabled={saving}>Enregistrer le brouillon</button>
          </div>
        </form>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-3">Annonce</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Statut</th>
              <th className="px-4 py-3">Visibilité</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">Aucune annonce.</td></tr>
            )}
            {items.map((n) => (
              <tr key={n.uuid} className="border-b border-slate-100 dark:border-slate-800 align-top">
                <td className="px-4 py-3">
                  <div className="font-semibold">{n.title}</div>
                  <div className="text-xs text-slate-500">{n.summary}</div>
                  {n.published_by_email && (
                    <div className="text-[10px] text-slate-400 mt-1">Publiée par {n.published_by_email} le {fmt(n.published_at)}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-xs">
                  <span className="inline-flex items-center gap-1">
                    <Megaphone className="h-3.5 w-3.5" /> {n.kind === 'alert' ? 'Alerte' : 'Recommandation'}
                  </span>
                </td>
                <td className="px-4 py-3"><span className={STATUS_BADGE[n.status]}>{STATUS_LABEL[n.status]}</span></td>
                <td className="px-4 py-3 text-xs">du {fmt(n.valid_from)} au {fmt(n.valid_until)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  {n.status !== 'published' && (
                    <button className="btn-primary text-xs" onClick={() => action(n, 'publish')}>
                      <Send className="h-3.5 w-3.5" /> Publier
                    </button>
                  )}
                  {n.status === 'published' && (
                    <button className="btn-outline text-xs" onClick={() => action(n, 'archive')}>
                      <Archive className="h-3.5 w-3.5" /> Archiver
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
