'use client';

/**
 * Pays à risque — référentiel pays et niveaux de risque sanitaire.
 *
 * Un niveau se définit par pays et par maladie, avec dates de validité,
 * justification et source (alerte sanitaire validée). Chaque saisie remplace
 * la précédente sans l'effacer : l'historique reste consultable.
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Globe2, History, Plus, X } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import {
  COUNTRY_RISK_BADGE, COUNTRY_RISK_LABEL, COUNTRY_RISK_OPTIONS, CountryRiskLevel,
} from '@/lib/countryRisk';

interface CurrentRisk {
  uuid: string; disease_code: string | null; disease_name: string | null;
  risk_level: CountryRiskLevel; valid_from: string; valid_until: string | null;
}
interface Country {
  id: number; code: string; code3: string; name: string; region: string;
  is_monitored: boolean; risk_level: CountryRiskLevel; current_risks: CurrentRisk[];
}
interface Disease { code: string; name: string }
interface Alert { uuid: string; title: string; severity: string; status: string }
interface Assessment {
  uuid: string; country: string; disease: string | null; disease_name: string | null;
  risk_level: CountryRiskLevel; valid_from: string; valid_until: string | null;
  justification: string; source_alert: string | null; source_reference: string;
  decided_by_email: string | null; superseded_by: string | null; is_current: boolean;
  created_at: string;
}

const today = () => new Date().toISOString().slice(0, 10);
const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');

const EMPTY_FORM = {
  disease: '', risk_level: 'moderate' as CountryRiskLevel, valid_from: today(), valid_until: '',
  justification: '', source_alert: '', source_reference: '',
};

export default function PaysRisquePage() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [monitoredOnly, setMonitoredOnly] = useState(true);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<Country | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [historyFor, setHistoryFor] = useState<Country | null>(null);
  const [history, setHistory] = useState<Assessment[]>([]);

  const loadCountries = useCallback(() => {
    api.get('/geo/countries/?page_size=300')
      .then((r) => setCountries(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);

  useEffect(() => {
    loadCountries();
    api.get('/diseases/?page_size=50')
      .then((r) => setDiseases(r.data.results || r.data))
      .catch(() => undefined);
    api.get('/surveillance/alerts/?page_size=50')
      .then((r) => setAlerts((r.data.results || r.data).filter((a: Alert) => a.status !== 'dismissed')))
      .catch(() => undefined);
  }, [loadCountries]);

  const loadHistory = (c: Country) => {
    setHistoryFor(c);
    api.get(`/geo/countries/${c.id}/risk-history/`)
      .then((r) => setHistory(r.data))
      .catch((e) => setErr(extractApiError(e)));
  };

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return countries
      .filter((c) => !monitoredOnly || c.is_monitored)
      .filter((c) => !q || [c.code, c.code3, c.name].some((v) => (v || '').toLowerCase().includes(q)));
  }, [countries, monitoredOnly, search]);

  const openForm = (c: Country) => {
    setEditing(c);
    setForm({ ...EMPTY_FORM, valid_from: today() });
    setFormErr(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setSaving(true);
    setFormErr(null);
    try {
      await api.post('/geo/country-risks/', {
        country: editing.code,
        disease: form.disease || null,
        risk_level: form.risk_level,
        valid_from: form.valid_from,
        valid_until: form.valid_until || null,
        justification: form.justification,
        source_alert: form.source_alert || null,
        source_reference: form.source_reference,
      });
      const c = editing;
      setEditing(null);
      loadCountries();
      if (historyFor?.id === c.id) loadHistory(c);
    } catch (e2) {
      setFormErr(extractApiError(e2));
    } finally {
      setSaving(false);
    }
  };

  const closeAssessment = async (a: Assessment) => {
    const reason = window.prompt('Justification de la fin de validité (obligatoire) :');
    if (!reason?.trim()) return;
    try {
      await api.post(`/geo/country-risks/${a.uuid}/close/`, { reason });
      loadCountries();
      if (historyFor) loadHistory(historyFor);
    } catch (e) {
      setErr(extractApiError(e));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Pays à risque</h1>
        <p className="text-sm text-slate-500 mt-1">
          Niveaux de risque sanitaire par pays et par maladie. Un niveau supérieur à « normal »
          doit s&apos;appuyer sur une alerte sanitaire validée.
        </p>
      </div>
      {err && <div className="card p-4 text-rose-600 text-sm">{err}</div>}

      <div className="card p-4 flex flex-wrap items-center gap-3">
        <Globe2 className="h-4 w-4 text-slate-500" />
        <input
          className="input max-w-xs text-sm"
          placeholder="Code ISO-2 / ISO-3 ou nom…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className="inline-flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={monitoredOnly} onChange={(e) => setMonitoredOnly(e.target.checked)} />
          Pays surveillés uniquement
        </label>
        <span className="text-xs text-slate-500 ml-auto">{visible.length} pays</span>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-3">Pays</th>
              <th className="px-4 py-3">ISO</th>
              <th className="px-4 py-3">Région</th>
              <th className="px-4 py-3">Niveau global</th>
              <th className="px-4 py-3">Par maladie (en vigueur)</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {visible.map((c) => (
              <tr key={c.code} className="border-b border-slate-100 dark:border-slate-800 align-top">
                <td className="px-4 py-3 font-semibold">
                  {c.name}
                  {c.is_monitored && <span className="ml-2 text-[10px] text-emerald-700 font-bold uppercase">surveillé</span>}
                </td>
                <td className="px-4 py-3 text-xs text-slate-500 tabular-nums">{c.code} · {c.code3 || '—'}</td>
                <td className="px-4 py-3 text-xs">{c.region || '—'}</td>
                <td className="px-4 py-3">
                  <span className={COUNTRY_RISK_BADGE[c.risk_level] || 'badge-low'}>
                    {COUNTRY_RISK_LABEL[c.risk_level] || c.risk_level}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {c.current_risks.length === 0 ? (
                    <span className="text-xs text-slate-400">Aucune évaluation</span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {c.current_risks.map((r) => (
                        <span key={r.uuid} className={COUNTRY_RISK_BADGE[r.risk_level]} title={`Depuis le ${fmt(r.valid_from)}${r.valid_until ? ` jusqu'au ${fmt(r.valid_until)}` : ''}`}>
                          {r.disease_code || 'Toutes'} · {COUNTRY_RISK_LABEL[r.risk_level]}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <button className="btn-ghost text-xs" onClick={() => loadHistory(c)}>
                    <History className="h-3.5 w-3.5" /> Historique
                  </button>
                  <button className="btn-outline text-xs ml-1" onClick={() => openForm(c)}>
                    <Plus className="h-3.5 w-3.5" /> Niveau
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <form onSubmit={submit} className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold">Nouveau niveau — {editing.name}</h2>
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)} aria-label="Fermer">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid md:grid-cols-4 gap-3">
            <label className="text-sm">Maladie
              <select className="select mt-1" value={form.disease} onChange={(e) => setForm({ ...form, disease: e.target.value })}>
                <option value="">Toutes maladies</option>
                {diseases.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
              </select>
            </label>
            <label className="text-sm">Niveau
              <select className="select mt-1" value={form.risk_level} onChange={(e) => setForm({ ...form, risk_level: e.target.value as CountryRiskLevel })}>
                {COUNTRY_RISK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label className="text-sm">En vigueur du
              <input type="date" className="input mt-1" required value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
            </label>
            <label className="text-sm">Jusqu&apos;au (optionnel)
              <input type="date" className="input mt-1" value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
            </label>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <label className="text-sm">Alerte de la plateforme
              <select className="select mt-1" value={form.source_alert} onChange={(e) => setForm({ ...form, source_alert: e.target.value })}>
                <option value="">— Aucune —</option>
                {alerts.map((a) => <option key={a.uuid} value={a.uuid}>[{a.severity}] {a.title}</option>)}
              </select>
            </label>
            <label className="text-sm">Référence de l&apos;alerte validée
              <input className="input mt-1" placeholder="Ex : bulletin OMS DON du 12/10/2026" value={form.source_reference} onChange={(e) => setForm({ ...form, source_reference: e.target.value })} />
            </label>
          </div>
          <label className="text-sm block">Justification
            <textarea className="textarea mt-1" required value={form.justification} onChange={(e) => setForm({ ...form, justification: e.target.value })} />
          </label>
          {formErr && <div className="text-sm text-rose-600">{formErr}</div>}
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>Annuler</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      )}

      {historyFor && (
        <section className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-lg font-bold">Historique — {historyFor.name}</h2>
            <button className="btn-ghost" onClick={() => setHistoryFor(null)} aria-label="Fermer">
              <X className="h-4 w-4" />
            </button>
          </div>
          {history.length === 0 ? (
            <p className="text-sm text-slate-400">Aucune évaluation enregistrée.</p>
          ) : (
            <ul className="space-y-2">
              {history.map((a) => (
                <li key={a.uuid} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={COUNTRY_RISK_BADGE[a.risk_level]}>{COUNTRY_RISK_LABEL[a.risk_level]}</span>
                    <span className="font-semibold">{a.disease_name || 'Toutes maladies'}</span>
                    <span className="text-xs text-slate-500">du {fmt(a.valid_from)} au {fmt(a.valid_until)}</span>
                    <span className="text-[10px] uppercase font-bold text-slate-500">
                      {a.superseded_by ? 'remplacée' : a.is_current ? 'en vigueur' : 'hors période'}
                    </span>
                    {a.is_current && (
                      <button className="btn-ghost text-xs ml-auto" onClick={() => closeAssessment(a)}>Clore</button>
                    )}
                  </div>
                  <p className="mt-1 text-slate-700 dark:text-slate-300">{a.justification}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Source : {a.source_reference || (a.source_alert ? `alerte ${a.source_alert}` : '—')}
                    {' · '}par {a.decided_by_email || 'système'} le {fmt(a.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
