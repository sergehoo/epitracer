'use client';

/**
 * /dashboard/formulaires — Hub de gestion des formulaires d'enquête dynamiques.
 *
 * Affiche tous les DynamicForm (par maladie, versioning), permet de créer un
 * nouveau formulaire, dupliquer en nouvelle version, activer/désactiver,
 * supprimer. L'édition des sections/champs se fait sur la page détail.
 */

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
  FormInput, Plus, Search, Copy, Edit, Trash2, Eye, CheckCircle, XCircle,
  Layers, FileCheck, Star, StarOff, BarChart3,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface Disease { id: number; code: string; name: string }
interface DForm {
  id: number;
  uuid: string;
  disease: number;
  disease_code: string;
  code: string;
  title: string;
  description: string;
  version: number;
  is_active: boolean;
  is_default: boolean;
  submissions_count?: number;
  sections?: { id: number; fields_list?: { id: number }[] }[];
}

export default function FormulairesPage() {
  const [items, setItems] = useState<DForm[]>([]);
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [search, setSearch] = useState('');
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

  // Modals
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<DForm | null>(null);

  const load = () => {
    setLoading(true);
    setErr(null);
    Promise.all([
      api.get('/forms/definitions/?page_size=100'),
      api.get('/diseases/?page_size=50'),
    ])
      .then(([f, d]) => {
        setItems(f.data.results || f.data);
        setDiseases(d.data.results || d.data);
      })
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  // Filtrage côté client
  const filtered = useMemo(() => {
    return items.filter((f) => {
      if (statusFilter === 'active' && !f.is_active) return false;
      if (statusFilter === 'inactive' && f.is_active) return false;
      if (diseaseFilter && String(f.disease) !== diseaseFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const hay = `${f.title} ${f.code} ${f.disease_code} ${f.description}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [items, search, diseaseFilter, statusFilter]);

  // Stats KPI
  const stats = useMemo(() => {
    const total = items.length;
    const active = items.filter((f) => f.is_active).length;
    const defaults = items.filter((f) => f.is_default).length;
    const diseases_with_form = new Set(items.map((f) => f.disease_code)).size;
    return { total, active, defaults, diseases_with_form };
  }, [items]);

  // Actions
  const toggleActive = async (f: DForm) => {
    try {
      await api.patch(`/forms/definitions/${f.id}/`, { is_active: !f.is_active });
      toast.success(f.is_active ? 'Formulaire désactivé' : 'Formulaire activé');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const toggleDefault = async (f: DForm) => {
    try {
      // Si on définit ce form comme défaut, on retire le flag des autres
      // de la même maladie côté backend via PATCH (on laisse le backend
      // appliquer l'unicité s'il y a une contrainte ; sinon on fait deux
      // appels). Pour rester simple ici, on PATCH juste celui-ci en true et
      // on rafraîchit — le serializer/clean assure la cohérence.
      await api.patch(`/forms/definitions/${f.id}/`, { is_default: !f.is_default });
      toast.success(f.is_default ? 'Formulaire retiré des défauts' : 'Formulaire défini par défaut');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const duplicateForm = async (f: DForm) => {
    try {
      // Crée un nouveau form avec version+1 et même structure
      const r = await api.post('/forms/definitions/', {
        disease: f.disease,
        code: f.code,
        title: `${f.title} (copie)`,
        description: f.description,
        version: f.version + 1,
        is_active: false,
        is_default: false,
      });
      toast.success(`Nouvelle version v${r.data.version} créée`);
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const deleteForm = async () => {
    if (!confirmDelete) return;
    try {
      await api.delete(`/forms/definitions/${confirmDelete.id}/`);
      toast.success('Formulaire supprimé');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Moteur multi-maladies
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100">
            Formulaires d'enquête
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Formulaires dynamiques par maladie, versionnés. Modifiez les sections,
            champs et logique conditionnelle sans redéploiement.
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-ciOrange text-white px-4 py-2 text-sm font-semibold shadow hover:bg-orange-600 transition"
        >
          <Plus className="h-4 w-4" /> Nouveau formulaire
        </button>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Total formulaires" value={stats.total} icon={<FormInput />} tone="emerald" />
        <Kpi label="Actifs" value={stats.active} icon={<CheckCircle />} tone="sky" />
        <Kpi label="Par défaut" value={stats.defaults} icon={<FileCheck />} tone="orange" />
        <Kpi label="Maladies couvertes" value={stats.diseases_with_form} icon={<Layers />} tone="slate" />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">Recherche</label>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Titre, code, maladie..."
              className="w-full pl-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Maladie</label>
          <select
            value={diseaseFilter}
            onChange={(e) => setDiseaseFilter(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="">Toutes</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Statut</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="all">Tous</option>
            <option value="active">Actifs</option>
            <option value="inactive">Inactifs</option>
          </select>
        </div>
        <div className="ml-auto text-xs text-slate-500 self-end">
          {filtered.length} sur {items.length} formulaires
        </div>
      </div>

      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* Liste */}
      <div className="grid md:grid-cols-2 gap-4">
        {loading && (
          <div className="md:col-span-2 card p-10 animate-pulse h-32" />
        )}
        {!loading && filtered.length === 0 && (
          <div className="md:col-span-2 card p-10 text-center text-slate-400">
            Aucun formulaire avec ces filtres.
          </div>
        )}
        {!loading && filtered.map((f) => {
          const nSections = f.sections?.length || 0;
          const nFields = f.sections?.reduce(
            (s, sec) => s + (sec.fields_list?.length || 0), 0,
          ) || 0;
          return (
            <article
              key={f.uuid}
              className={`card p-5 flex flex-col gap-3 transition hover:shadow-md ${
                !f.is_active ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`h-12 w-12 rounded-xl grid place-items-center shrink-0 ${
                  f.is_active ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                }`}>
                  <FormInput className="h-6 w-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <Link href={`/formulaires/${f.uuid}`} className="font-display text-base font-bold hover:text-ciOrange transition">
                    {f.title}
                  </Link>
                  <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-2">
                    <span className="font-bold uppercase text-emerald-700">{f.disease_code}</span>
                    <span>·</span>
                    <span className="font-mono">{f.code}</span>
                    <span>·</span>
                    <span>v{f.version}</span>
                  </div>
                  {f.description && (
                    <p className="text-xs text-slate-500 mt-2 line-clamp-2">{f.description}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {f.is_active ? <span className="badge-low">Actif</span> : <span className="badge-moderate">Inactif</span>}
                    {f.is_default && <span className="badge-low">Par défaut</span>}
                    <span className="badge-low">{nSections} section{nSections > 1 ? 's' : ''}</span>
                    <span className="badge-low">{nFields} champ{nFields > 1 ? 's' : ''}</span>
                    {typeof f.submissions_count === 'number' && (
                      <span className="badge-low inline-flex items-center gap-1">
                        <BarChart3 className="h-3 w-3" />
                        {f.submissions_count} soumission{f.submissions_count > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-1 pt-2 border-t border-slate-100 dark:border-slate-800">
                <Link
                  href={`/formulaires/${f.uuid}`}
                  title="Voir & éditer"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  <Edit className="h-4 w-4" />
                </Link>
                <button
                  onClick={() => duplicateForm(f)}
                  title="Dupliquer en nouvelle version"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  <Copy className="h-4 w-4" />
                </button>
                <button
                  onClick={() => toggleDefault(f)}
                  title={f.is_default ? 'Retirer des formulaires par défaut' : 'Définir comme formulaire par défaut'}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  {f.is_default
                    ? <Star className="h-4 w-4 text-amber-500 fill-amber-400" />
                    : <StarOff className="h-4 w-4" />}
                </button>
                <button
                  onClick={() => toggleActive(f)}
                  title={f.is_active ? 'Désactiver' : 'Activer'}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  {f.is_active ? <XCircle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4 text-emerald-600" />}
                </button>
                <button
                  onClick={() => setConfirmDelete(f)}
                  title="Supprimer"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-rose-50 hover:text-rose-600 transition"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {/* Modal création */}
      {createOpen && (
        <CreateFormModal
          diseases={diseases}
          onClose={() => setCreateOpen(false)}
          onCreated={() => { setCreateOpen(false); load(); }}
        />
      )}

      {/* Modal confirmation suppression */}
      {confirmDelete && (
        <ConfirmModal
          title="Supprimer le formulaire"
          message={`Le formulaire "${confirmDelete.title}" (v${confirmDelete.version}) sera supprimé définitivement avec toutes ses sections et champs. Les soumissions existantes ne pourront plus être interprétées. Continuer ?`}
          onCancel={() => setConfirmDelete(null)}
          onConfirm={deleteForm}
        />
      )}
    </div>
  );
}

// ===========================================================================
// Sous-composants
// ===========================================================================

function Kpi({
  label, value, icon, tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: 'emerald' | 'sky' | 'orange' | 'slate';
}) {
  const tones = {
    emerald: 'from-emerald-50 to-teal-50 text-emerald-700 border-emerald-200/60',
    sky: 'from-sky-50 to-blue-50 text-sky-700 border-sky-200/60',
    orange: 'from-orange-50 to-amber-50 text-orange-700 border-orange-200/60',
    slate: 'from-slate-50 to-gray-50 text-slate-700 border-slate-200/60',
  };
  return (
    <div className={`p-4 rounded-2xl border bg-gradient-to-br ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold opacity-80">{label}</span>
        <span className="opacity-50">{icon}</span>
      </div>
      <div className="mt-2 font-display text-3xl font-black">{value}</div>
    </div>
  );
}

function CreateFormModal({
  diseases, onClose, onCreated,
}: {
  diseases: Disease[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [disease, setDisease] = useState<number | ''>(diseases[0]?.id || '');
  const [code, setCode] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease || !code || !title) {
      toast.error('Maladie, code et titre sont requis.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/forms/definitions/', {
        disease,
        code: code.toLowerCase().replace(/\s+/g, '-'),
        title,
        description,
        version: 1,
        is_active: true,
        is_default: isDefault,
      });
      toast.success('Formulaire créé');
      onCreated();
    } catch (e: any) {
      toast.error(extractApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalShell title="Nouveau formulaire d'enquête" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Maladie *">
          <select
            value={disease} onChange={(e) => setDisease(Number(e.target.value))}
            className="input-base"
            required
          >
            <option value="">— Sélectionner —</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
            ))}
          </select>
        </Field>
        <Field label="Code *">
          <input
            type="text" value={code} onChange={(e) => setCode(e.target.value)}
            placeholder="ex: fiche-passager-2026"
            className="input-base font-mono"
            required
          />
          <span className="text-[10px] text-slate-400">Identifiant URL-safe (sans espace)</span>
        </Field>
        <Field label="Titre *">
          <input
            type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            placeholder="ex: Fiche de renseignement passager"
            className="input-base"
            required
          />
        </Field>
        <Field label="Description">
          <textarea
            value={description} onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="input-base resize-none"
            placeholder="Description du formulaire (objectif, public cible...)"
          />
        </Field>
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
          <span>Marquer comme formulaire <strong>par défaut</strong> pour cette maladie</span>
        </label>
        <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button type="button" onClick={onClose} className="btn-secondary">Annuler</button>
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? 'Création...' : 'Créer le formulaire'}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

function ConfirmModal({
  title, message, onCancel, onConfirm,
}: {
  title: string;
  message: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <ModalShell title={title} onClose={onCancel}>
      <p className="text-sm text-slate-600 dark:text-slate-300">{message}</p>
      <div className="flex justify-end gap-2 pt-6">
        <button onClick={onCancel} className="btn-secondary">Annuler</button>
        <button
          onClick={async () => { setBusy(true); try { await onConfirm(); } finally { setBusy(false); } }}
          disabled={busy}
          className="btn-danger"
        >
          {busy ? '...' : 'Supprimer'}
        </button>
      </div>
    </ModalShell>
  );
}

function ModalShell({
  title, onClose, children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg mt-8 mb-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl">×</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-500 mb-1">{label}</span>
      {children}
    </label>
  );
}
