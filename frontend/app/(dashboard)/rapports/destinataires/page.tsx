'use client';

/**
 * /dashboard/rapports/destinataires — CRUD des destinataires de rapports.
 *
 * Gestion réservée à NATIONAL_ADMIN / INHP (backend permission
 * CanManageReportRecipients). Filtres canal / district / actif + import CSV
 * en dry-run + export CSV + test-envoi individuel.
 */

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
  ArrowLeft, Bell, CheckCircle2, Download, Edit3, Mail, Plus, Search,
  Send, Smartphone, Trash2, Upload, Users, X, XCircle,
} from 'lucide-react';
import { api, extractApiError, API_URL } from '@/lib/api';


interface Recipient {
  id: number;
  full_name: string;
  organization: string;
  preferred_channel: 'sms' | 'email' | 'both';
  preferred_channel_label?: string;
  masked_phone: string;
  email: string;
  is_active: boolean;
  // Champs uniquement présents dans le serializer détail
  job_title?: string;
  phone_number?: string;
  language?: string;
  district?: number | null;
  district_name?: string | null;
  allowed_report_types?: string[];
  consent_date?: string | null;
  consent_evidence?: string;
  created_at?: string;
  updated_at?: string;
}

const CHANNEL_META: Record<Recipient['preferred_channel'], { icon: React.ReactNode; label: string; color: string }> = {
  sms: { icon: <Smartphone className="h-3.5 w-3.5" />, label: 'SMS', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  email: { icon: <Mail className="h-3.5 w-3.5" />, label: 'Email', color: 'bg-sky-100 text-sky-700 border-sky-300' },
  both: { icon: <Bell className="h-3.5 w-3.5" />, label: 'SMS + Email', color: 'bg-ciOrange/20 text-orange-700 border-orange-300' },
};


export default function RecipientsPage() {
  const [rows, setRows] = useState<Recipient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtres
  const [q, setQ] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');

  // Modals
  const [editTarget, setEditTarget] = useState<Recipient | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set('q', q.trim());
      if (channelFilter) params.set('preferred_channel', channelFilter);
      if (activeFilter) params.set('is_active', activeFilter);
      params.set('page_size', '200');
      const { data } = await api.get<{ results?: Recipient[] } | Recipient[]>(
        `/reports/recipients/?${params}`,
      );
      setRows(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [q, channelFilter, activeFilter]);

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [load]);

  const doDelete = async (r: Recipient) => {
    if (!confirm(`Désactiver le destinataire "${r.full_name}" ?`)) return;
    try {
      await api.delete(`/reports/recipients/${r.id}/`);
      toast.success('Destinataire désactivé.');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const doTest = async (r: Recipient, channel: 'sms' | 'email') => {
    try {
      await api.post(`/reports/recipients/${r.id}/test/`, { channel });
      toast.success(`Test ${channel.toUpperCase()} envoyé à ${r.full_name}.`);
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const kpi = useMemo(() => ({
    total: rows.length,
    active: rows.filter(r => r.is_active).length,
    sms: rows.filter(r => r.preferred_channel === 'sms' || r.preferred_channel === 'both').length,
    email: rows.filter(r => r.preferred_channel === 'email' || r.preferred_channel === 'both').length,
  }), [rows]);

  return (
    <div className="space-y-6">
      <header>
        <Link href="/rapports" className="text-xs text-slate-500 hover:text-ciOrange inline-flex items-center gap-1 mb-2">
          <ArrowLeft className="h-3 w-3" /> Retour au Centre de rapports
        </Link>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
              Rapports · Destinataires
            </span>
            <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
              Gérer les destinataires
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
              Liste des personnes qui reçoivent le rapport hebdomadaire par SMS et/ou email.
              Le consentement écrit est obligatoire (conformité RGPD nationale INHP).
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setImportOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Upload className="h-3.5 w-3.5" /> Import CSV
            </button>
            <a
              href={`${API_URL}/api/v1/reports/recipients/export-csv/`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </a>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-ciOrange text-white px-4 py-2 text-sm font-bold shadow hover:bg-orange-600"
            >
              <Plus className="h-4 w-4" /> Ajouter
            </button>
          </div>
        </div>
      </header>

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiTile label="Total" value={kpi.total} color="text-ciDark dark:text-emerald-200" />
        <KpiTile label="Actifs" value={kpi.active} color="text-ciGreen" />
        <KpiTile label="Canal SMS" value={kpi.sms} color="text-emerald-600" />
        <KpiTile label="Canal Email" value={kpi.email} color="text-sky-600" />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Rechercher (nom, email, organisation)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          className="select max-w-[180px]"
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value)}
        >
          <option value="">Tous canaux</option>
          <option value="sms">SMS uniquement</option>
          <option value="email">Email uniquement</option>
          <option value="both">SMS + Email</option>
        </select>
        <select
          className="select max-w-[160px]"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="">Actifs & inactifs</option>
          <option value="true">Actifs seulement</option>
          <option value="false">Inactifs seulement</option>
        </select>
      </div>

      {error && (
        <div className="card p-4 bg-rose-50 border-rose-200 text-rose-700 text-sm">
          {error}
        </div>
      )}

      {/* Tableau */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Nom</th>
                <th className="px-3 py-2">Organisation</th>
                <th className="px-3 py-2">Canal</th>
                <th className="px-3 py-2">Contact</th>
                <th className="px-3 py-2">Statut</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6} className="p-8 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={6} className="p-8 text-center text-slate-400">
                  Aucun destinataire. Cliquez sur « Ajouter » pour créer le premier.
                </td></tr>
              )}
              {!loading && rows.map(r => {
                const meta = CHANNEL_META[r.preferred_channel];
                return (
                  <tr key={r.id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                    <td className="px-3 py-2.5">
                      <div className="font-semibold">{r.full_name}</div>
                      {r.job_title && <div className="text-[11px] text-slate-500">{r.job_title}</div>}
                    </td>
                    <td className="px-3 py-2.5 text-xs">{r.organization || '—'}</td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold border ${meta.color}`}>
                        {meta.icon} {meta.label}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-xs font-mono">
                      {(r.preferred_channel === 'sms' || r.preferred_channel === 'both') && r.masked_phone && (
                        <div>{r.masked_phone}</div>
                      )}
                      {(r.preferred_channel === 'email' || r.preferred_channel === 'both') && r.email && (
                        <div className="text-slate-500">{r.email}</div>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {r.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-bold">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Actif
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-500 text-xs font-bold">
                          <XCircle className="h-3.5 w-3.5" /> Inactif
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="inline-flex items-center gap-1">
                        {(r.preferred_channel === 'sms' || r.preferred_channel === 'both') && (
                          <button
                            onClick={() => doTest(r, 'sms')}
                            title="Envoyer un SMS test [TEST]"
                            className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 text-[11px] font-semibold hover:border-emerald-400"
                          >
                            <Send className="h-3 w-3 text-emerald-600" /> SMS
                          </button>
                        )}
                        {(r.preferred_channel === 'email' || r.preferred_channel === 'both') && (
                          <button
                            onClick={() => doTest(r, 'email')}
                            title="Envoyer un email test [TEST]"
                            className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 text-[11px] font-semibold hover:border-sky-400"
                          >
                            <Mail className="h-3 w-3 text-sky-600" /> Email
                          </button>
                        )}
                        <button
                          onClick={() => setEditTarget(r)}
                          title="Modifier"
                          className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 text-[11px] font-semibold hover:border-ciOrange"
                        >
                          <Edit3 className="h-3 w-3" />
                        </button>
                        <button
                          onClick={() => doDelete(r)}
                          title="Désactiver"
                          className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 text-[11px] font-semibold hover:border-rose-400"
                        >
                          <Trash2 className="h-3 w-3 text-rose-600" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {(showCreate || editTarget) && (
        <RecipientModal
          initial={editTarget}
          onClose={() => { setShowCreate(false); setEditTarget(null); }}
          onSaved={() => { setShowCreate(false); setEditTarget(null); load(); }}
        />
      )}

      {importOpen && (
        <ImportCsvModal
          onClose={() => setImportOpen(false)}
          onDone={() => { setImportOpen(false); load(); }}
        />
      )}
    </div>
  );
}


// ---------------------------------------------------------------------- Modal add/edit
function RecipientModal({ initial, onClose, onSaved }: {
  initial: Recipient | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    full_name: initial?.full_name ?? '',
    job_title: initial?.job_title ?? '',
    organization: initial?.organization ?? '',
    phone_number: initial?.phone_number ?? '',
    email: initial?.email ?? '',
    preferred_channel: (initial?.preferred_channel ?? 'email') as 'sms' | 'email' | 'both',
    language: initial?.language ?? 'fr',
    is_active: initial?.is_active ?? true,
    consent_date: initial?.consent_date ?? '',
    consent_evidence: initial?.consent_evidence ?? '',
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!form.full_name.trim()) {
      toast.error('Nom complet requis.');
      return;
    }
    if (form.is_active && !form.consent_date) {
      toast.error('Le consentement (date) est obligatoire pour activer.');
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form, consent_date: form.consent_date || null };
      if (initial) {
        await api.patch(`/reports/recipients/${initial.id}/`, payload);
        toast.success('Destinataire mis à jour.');
      } else {
        await api.post('/reports/recipients/', payload);
        toast.success('Destinataire créé.');
      }
      onSaved();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl font-black text-ciDark dark:text-emerald-100">
            {initial ? 'Modifier le destinataire' : 'Nouveau destinataire'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <Field label="Nom complet *">
            <input className="input" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fonction">
              <input className="input" value={form.job_title} onChange={e => setForm({ ...form, job_title: e.target.value })} />
            </Field>
            <Field label="Organisation">
              <input className="input" value={form.organization} onChange={e => setForm({ ...form, organization: e.target.value })} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Téléphone (+225…)">
              <input className="input font-mono" value={form.phone_number} onChange={e => setForm({ ...form, phone_number: e.target.value })} placeholder="+22507XXXXXXXX" />
            </Field>
            <Field label="Email">
              <input className="input" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="jean.dupont@inhp.ci" />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Canal préféré *">
              <select
                className="select"
                value={form.preferred_channel}
                onChange={e => setForm({ ...form, preferred_channel: e.target.value as 'sms' | 'email' | 'both' })}
              >
                <option value="email">Email uniquement</option>
                <option value="sms">SMS uniquement</option>
                <option value="both">SMS + Email</option>
              </select>
            </Field>
            <Field label="Langue">
              <select className="select" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}>
                <option value="fr">Français</option>
                <option value="en">English</option>
              </select>
            </Field>
          </div>

          <fieldset className="border border-amber-200 bg-amber-50/50 rounded-xl p-4 space-y-3">
            <legend className="text-xs font-bold text-amber-800 px-1">Consentement (obligatoire pour activer)</legend>
            <Field label="Date de recueil du consentement">
              <input type="date" className="input" value={form.consent_date} onChange={e => setForm({ ...form, consent_date: e.target.value })} />
            </Field>
            <Field label="Preuve (URL ou référence document)">
              <input className="input" value={form.consent_evidence} onChange={e => setForm({ ...form, consent_evidence: e.target.value })} placeholder="ex. Contrat INHP-DIST-2026-042" />
            </Field>
          </fieldset>

          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input type="checkbox" className="accent-ciOrange" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
            <span className="text-sm font-semibold">Actif — recevra les rapports</span>
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-bold">Annuler</button>
          <button onClick={save} disabled={saving} className="px-4 py-2 rounded-lg bg-ciOrange text-white text-sm font-bold hover:bg-orange-600 disabled:opacity-50">
            {saving ? 'Enregistrement…' : (initial ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------- Modal import CSV
function ImportCsvModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ created_or_updated: number; skipped: number; errors: { line: number; error: string }[] } | null>(null);

  const submit = async () => {
    if (!file) { toast.error('Sélectionnez un fichier CSV.'); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('csv_file', file);
      fd.append('dry_run', dryRun ? 'true' : 'false');
      const { data } = await api.post('/reports/recipients/import-csv/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(data);
      if (!dryRun) {
        toast.success(`${data.created_or_updated} destinataire(s) importé(s).`);
      }
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl font-black text-ciDark dark:text-emerald-100">
            Import CSV — destinataires
          </h2>
          <button onClick={onClose} className="text-slate-400"><X className="h-5 w-5" /></button>
        </div>

        <div className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded-lg p-3 mb-4">
          <strong>Colonnes attendues</strong> (séparateur <code>,</code> ou <code>;</code>) :<br />
          <code className="font-mono text-[11px]">full_name;job_title;organization;phone_number;email;preferred_channel;consent_date;consent_evidence</code>
        </div>

        <div className="space-y-3">
          <input
            type="file"
            accept=".csv,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="input"
          />
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="accent-ciOrange" />
            <span className="text-sm">Mode simulation (rien n'est écrit en base)</span>
          </label>
        </div>

        {result && (
          <div className="mt-4 rounded-lg border border-slate-200 dark:border-slate-700 p-3 text-sm">
            <div>Traité : <strong>{result.created_or_updated}</strong> · Ignorés : <strong>{result.skipped}</strong></div>
            {result.errors.length > 0 && (
              <ul className="mt-2 text-xs text-rose-700 max-h-40 overflow-auto">
                {result.errors.map((e, i) => <li key={i}>Ligne {e.line} : {e.error}</li>)}
              </ul>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-bold">Fermer</button>
          <button onClick={submit} disabled={busy || !file} className="px-4 py-2 rounded-lg bg-ciOrange text-white text-sm font-bold hover:bg-orange-600 disabled:opacity-50">
            {busy ? 'Import…' : (dryRun ? 'Simuler' : 'Importer')}
          </button>
          {result && !dryRun && result.created_or_updated > 0 && (
            <button onClick={onDone} className="px-4 py-2 rounded-lg bg-ciGreen text-white text-sm font-bold hover:opacity-90">
              Terminer
            </button>
          )}
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------- helpers
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">{label}</div>
      {children}
    </label>
  );
}

function KpiTile({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold">{label}</div>
      <div className={`mt-1 font-display text-2xl md:text-3xl font-black ${color}`}>{value.toLocaleString('fr-FR')}</div>
    </div>
  );
}
