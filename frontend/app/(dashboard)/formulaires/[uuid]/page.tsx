'use client';

/**
 * /dashboard/formulaires/[uuid] — Éditeur visuel d'un DynamicForm.
 *
 * Affiche l'arborescence Sections → Champs avec :
 *   - Édition métadonnées du formulaire
 *   - Ajout / édition / suppression de sections
 *   - Ajout / édition / suppression de champs (avec tous les paramètres :
 *     type, validations, options pour select/radio/checkbox)
 *   - Réordonnancement par champ "order" (boutons ↑↓)
 */

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import toast from 'react-hot-toast';
import {
  ArrowLeft, Plus, Edit, Trash2, Save, ChevronUp, ChevronDown,
  Settings, Eye, AlertCircle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

// =========================================================================
// Types
// =========================================================================

interface FormOption { id: number; value: string; label: string; order: number; triggers_risk?: boolean }
interface FormField {
  id: number;
  section: number;
  code: string;
  label: string;
  help_text: string;
  type: string;
  is_required: boolean;
  order: number;
  min_value?: number | null;
  max_value?: number | null;
  min_length?: number | null;
  max_length?: number | null;
  regex?: string;
  default_value?: string;
  placeholder?: string;
  risk_weight?: number;
  options?: FormOption[];
}
interface FormSection {
  id: number;
  form: number;
  code: string;
  title: string;
  description: string;
  order: number;
  fields_list?: FormField[];
}
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
  sections?: FormSection[];
}

const FIELD_TYPES = [
  { value: 'text', label: 'Texte court' },
  { value: 'textarea', label: 'Texte long' },
  { value: 'number', label: 'Nombre' },
  { value: 'integer', label: 'Entier' },
  { value: 'phone', label: 'Téléphone' },
  { value: 'email', label: 'Email' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'Date & heure' },
  { value: 'boolean', label: 'Oui / Non' },
  { value: 'yes_no_unknown', label: 'Oui / Non / Ne sait pas' },
  { value: 'select', label: 'Liste déroulante' },
  { value: 'multiselect', label: 'Liste à choix multiples' },
  { value: 'radio', label: 'Boutons radio' },
  { value: 'checkbox', label: 'Cases à cocher' },
  { value: 'geolocation', label: 'Géolocalisation' },
  { value: 'qr_scan', label: 'Scan QR code' },
  { value: 'image', label: 'Image (upload)' },
  { value: 'file', label: 'Fichier (upload)' },
  { value: 'signature', label: 'Signature' },
  { value: 'country', label: 'Pays (ISO-2)' },
];

const TYPES_WITH_OPTIONS = ['select', 'multiselect', 'radio', 'checkbox'];
const TYPES_WITH_RANGE = ['number', 'integer'];
const TYPES_WITH_LENGTH = ['text', 'textarea', 'phone'];

// =========================================================================
// Page
// =========================================================================

export default function FormDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid || '';
  const [form, setForm] = useState<DForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [editFormOpen, setEditFormOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<FormSection | null>(null);
  const [addSectionOpen, setAddSectionOpen] = useState(false);
  const [editingField, setEditingField] = useState<FormField | null>(null);
  const [addFieldFor, setAddFieldFor] = useState<FormSection | null>(null);

  const load = useCallback(async () => {
    if (!uuid) return;
    setLoading(true);
    try {
      // Récupérer le form complet via l'endpoint detail (DRF lookup = id par défaut)
      // L'UUID n'étant pas le lookup_field, on filtre par uuid puis on récupère le 1er.
      const r = await api.get(`/forms/definitions/?uuid=${uuid}&page_size=1`);
      const data: any = r.data;
      const list = data.results || data;
      if (list?.[0]) {
        // On récupère le détail via /definitions/<id>/ pour avoir toutes les relations
        const detail = await api.get(`/forms/definitions/${list[0].id}/`);
        setForm(detail.data);
      } else {
        setError('Formulaire introuvable.');
      }
    } catch (e: any) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  useEffect(() => { load(); }, [load]);

  // Actions section
  const moveSectionOrder = async (sec: FormSection, delta: number) => {
    try {
      await api.patch(`/forms/sections/${sec.id}/`, { order: Math.max(0, sec.order + delta) });
      load();
    } catch (e: any) { toast.error(extractApiError(e)); }
  };
  const deleteSection = async (sec: FormSection) => {
    if (!confirm(`Supprimer la section "${sec.title}" et tous ses champs ?`)) return;
    try {
      await api.delete(`/forms/sections/${sec.id}/`);
      toast.success('Section supprimée');
      load();
    } catch (e: any) { toast.error(extractApiError(e)); }
  };

  // Actions field
  const moveFieldOrder = async (field: FormField, delta: number) => {
    try {
      await api.patch(`/forms/fields/${field.id}/`, { order: Math.max(0, field.order + delta) });
      load();
    } catch (e: any) { toast.error(extractApiError(e)); }
  };
  const deleteField = async (field: FormField) => {
    if (!confirm(`Supprimer le champ "${field.label}" ?`)) return;
    try {
      await api.delete(`/forms/fields/${field.id}/`);
      toast.success('Champ supprimé');
      load();
    } catch (e: any) { toast.error(extractApiError(e)); }
  };

  if (loading) return <div className="card p-10 animate-pulse h-64" />;
  if (error) return <div className="card p-6 text-rose-600">{error}</div>;
  if (!form) return <div className="card p-6 text-slate-500">Formulaire introuvable.</div>;

  const sections = (form.sections || []).slice().sort((a, b) => a.order - b.order);

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/formulaires" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange">
        <ArrowLeft className="h-3 w-3" /> Tous les formulaires
      </Link>

      {/* En-tête */}
      <header className="card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs uppercase tracking-widest text-emerald-700 font-bold">{form.disease_code}</span>
              <span className="text-xs font-mono text-slate-400">{form.code}</span>
              <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">v{form.version}</span>
              {form.is_active ? <span className="badge-low">Actif</span> : <span className="badge-moderate">Inactif</span>}
              {form.is_default && <span className="badge-low">Par défaut</span>}
            </div>
            <h1 className="font-display text-2xl md:text-3xl font-black mt-1">{form.title}</h1>
            {form.description && (
              <p className="text-sm text-slate-500 mt-2 max-w-3xl">{form.description}</p>
            )}
          </div>
          <button
            onClick={() => setEditFormOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-100 dark:bg-slate-800 px-3 py-2 text-sm font-semibold hover:bg-slate-200 dark:hover:bg-slate-700"
          >
            <Settings className="h-4 w-4" /> Paramètres
          </button>
        </div>
      </header>

      {/* Sections */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold">
            {sections.length} section{sections.length > 1 ? 's' : ''}
          </h2>
          <button
            onClick={() => setAddSectionOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ciOrange text-white px-3 py-1.5 text-sm font-semibold hover:bg-orange-600"
          >
            <Plus className="h-4 w-4" /> Section
          </button>
        </div>

        {sections.length === 0 && (
          <div className="card p-10 text-center text-slate-400">
            Aucune section. Cliquez sur « + Section » pour commencer.
          </div>
        )}

        {sections.map((sec, ix) => {
          const fields = (sec.fields_list || []).slice().sort((a, b) => a.order - b.order);
          return (
            <article key={sec.id} className="card overflow-hidden">
              <header className="flex items-center gap-3 px-5 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
                <div className="h-8 w-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 grid place-items-center font-bold text-sm">
                  {ix + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-base font-bold">{sec.title}</div>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                    {sec.code} · {fields.length} champ{fields.length > 1 ? 's' : ''}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <ActionIcon title="Monter" onClick={() => moveSectionOrder(sec, -1)} disabled={ix === 0}>
                    <ChevronUp className="h-4 w-4" />
                  </ActionIcon>
                  <ActionIcon title="Descendre" onClick={() => moveSectionOrder(sec, 1)} disabled={ix === sections.length - 1}>
                    <ChevronDown className="h-4 w-4" />
                  </ActionIcon>
                  <ActionIcon title="Éditer la section" onClick={() => setEditingSection(sec)}>
                    <Edit className="h-4 w-4" />
                  </ActionIcon>
                  <ActionIcon title="Supprimer" danger onClick={() => deleteSection(sec)}>
                    <Trash2 className="h-4 w-4" />
                  </ActionIcon>
                </div>
              </header>

              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {fields.length === 0 ? (
                  <div className="p-5 text-center text-xs text-slate-400">
                    Aucun champ dans cette section.
                  </div>
                ) : (
                  fields.map((field, fi) => (
                    <div key={field.id} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50/40 dark:hover:bg-slate-900/40">
                      <span className="text-[10px] font-mono text-slate-400 w-6 text-right">#{field.order}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm">{field.label}</span>
                          {field.is_required && <span className="text-rose-500 text-xs">*</span>}
                          <span className="text-[10px] bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300 px-1.5 py-0.5 rounded font-mono">
                            {FIELD_TYPES.find((t) => t.value === field.type)?.label || field.type}
                          </span>
                          {field.risk_weight && field.risk_weight > 0 && (
                            <span className="text-[10px] bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded">
                              ⚠ score +{field.risk_weight}
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          {field.code}
                          {(field.options?.length || 0) > 0 && ` · ${field.options!.length} option${field.options!.length > 1 ? 's' : ''}`}
                          {field.help_text && ` · ${field.help_text}`}
                        </div>
                      </div>
                      <div className="flex items-center gap-0.5">
                        <ActionIcon title="Monter" onClick={() => moveFieldOrder(field, -1)} disabled={fi === 0}>
                          <ChevronUp className="h-4 w-4" />
                        </ActionIcon>
                        <ActionIcon title="Descendre" onClick={() => moveFieldOrder(field, 1)} disabled={fi === fields.length - 1}>
                          <ChevronDown className="h-4 w-4" />
                        </ActionIcon>
                        <ActionIcon title="Éditer" onClick={() => setEditingField(field)}>
                          <Edit className="h-4 w-4" />
                        </ActionIcon>
                        <ActionIcon title="Supprimer" danger onClick={() => deleteField(field)}>
                          <Trash2 className="h-4 w-4" />
                        </ActionIcon>
                      </div>
                    </div>
                  ))
                )}
                <div className="px-5 py-2">
                  <button
                    onClick={() => setAddFieldFor(sec)}
                    className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline font-semibold"
                  >
                    <Plus className="h-3 w-3" /> Ajouter un champ
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </section>

      {/* Modals */}
      {editFormOpen && (
        <FormMetaModal form={form} onClose={() => setEditFormOpen(false)} onSaved={() => { setEditFormOpen(false); load(); }} />
      )}
      {addSectionOpen && (
        <SectionModal form={form} onClose={() => setAddSectionOpen(false)} onSaved={() => { setAddSectionOpen(false); load(); }} />
      )}
      {editingSection && (
        <SectionModal form={form} section={editingSection} onClose={() => setEditingSection(null)} onSaved={() => { setEditingSection(null); load(); }} />
      )}
      {addFieldFor && (
        <FieldModal section={addFieldFor} onClose={() => setAddFieldFor(null)} onSaved={() => { setAddFieldFor(null); load(); }} />
      )}
      {editingField && (
        <FieldModal
          section={sections.find((s) => s.id === editingField.section)!}
          field={editingField}
          onClose={() => setEditingField(null)}
          onSaved={() => { setEditingField(null); load(); }}
        />
      )}
    </div>
  );
}

// =========================================================================
// Helpers UI
// =========================================================================

function ActionIcon({ children, title, onClick, danger, disabled }: {
  children: React.ReactNode; title: string; onClick: () => void; danger?: boolean; disabled?: boolean;
}) {
  return (
    <button
      type="button" title={title} onClick={onClick} disabled={disabled}
      className={`inline-flex h-7 w-7 items-center justify-center rounded-md transition disabled:opacity-30 ${
        danger ? 'hover:bg-rose-50 hover:text-rose-600' : 'hover:bg-slate-100 dark:hover:bg-slate-800'
      }`}
    >
      {children}
    </button>
  );
}

function ModalShell({ title, onClose, children, wide }: {
  title: string; onClose: () => void; children: React.ReactNode; wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className={`bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} mt-8 mb-8`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl">×</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block ${className || ''}`}>
      <span className="block text-xs font-medium text-slate-500 mb-1">{label}</span>
      {children}
    </label>
  );
}

// =========================================================================
// Modal métadonnées formulaire
// =========================================================================

function FormMetaModal({ form, onClose, onSaved }: { form: DForm; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(form.title);
  const [description, setDescription] = useState(form.description);
  const [isActive, setIsActive] = useState(form.is_active);
  const [isDefault, setIsDefault] = useState(form.is_default);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch(`/forms/definitions/${form.id}/`, {
        title, description, is_active: isActive, is_default: isDefault,
      });
      toast.success('Formulaire mis à jour');
      onSaved();
    } catch (e: any) { toast.error(extractApiError(e)); } finally { setBusy(false); }
  };

  return (
    <ModalShell title="Paramètres du formulaire" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Titre"><input value={title} onChange={(e) => setTitle(e.target.value)} className="input-base" required /></Field>
        <Field label="Description"><textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className="input-base resize-none" /></Field>
        <div className="flex gap-4">
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Actif
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
            Par défaut pour cette maladie
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button type="button" onClick={onClose} className="btn-secondary">Annuler</button>
          <button type="submit" disabled={busy} className="btn-primary">{busy ? '...' : 'Enregistrer'}</button>
        </div>
      </form>
    </ModalShell>
  );
}

// =========================================================================
// Modal section
// =========================================================================

function SectionModal({ form, section, onClose, onSaved }: {
  form: DForm; section?: FormSection; onClose: () => void; onSaved: () => void;
}) {
  const isEdit = !!section;
  const [code, setCode] = useState(section?.code || '');
  const [title, setTitle] = useState(section?.title || '');
  const [description, setDescription] = useState(section?.description || '');
  const [order, setOrder] = useState(section?.order ?? (form.sections?.length || 0));
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { form: form.id, code, title, description, order };
      if (isEdit) await api.patch(`/forms/sections/${section!.id}/`, payload);
      else await api.post('/forms/sections/', payload);
      toast.success(isEdit ? 'Section mise à jour' : 'Section créée');
      onSaved();
    } catch (e: any) { toast.error(extractApiError(e)); } finally { setBusy(false); }
  };

  return (
    <ModalShell title={isEdit ? `Éditer : ${section!.title}` : 'Nouvelle section'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Code *"><input value={code} onChange={(e) => setCode(e.target.value)} className="input-base font-mono" required placeholder="section-1" /></Field>
        <Field label="Titre *"><input value={title} onChange={(e) => setTitle(e.target.value)} className="input-base" required /></Field>
        <Field label="Description"><textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className="input-base resize-none" /></Field>
        <Field label="Ordre"><input type="number" value={order} onChange={(e) => setOrder(Number(e.target.value))} className="input-base" /></Field>
        <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button type="button" onClick={onClose} className="btn-secondary">Annuler</button>
          <button type="submit" disabled={busy} className="btn-primary">{busy ? '...' : (isEdit ? 'Enregistrer' : 'Créer')}</button>
        </div>
      </form>
    </ModalShell>
  );
}

// =========================================================================
// Modal champ (le plus gros — tous les paramètres)
// =========================================================================

function FieldModal({ section, field, onClose, onSaved }: {
  section: FormSection; field?: FormField; onClose: () => void; onSaved: () => void;
}) {
  const isEdit = !!field;
  const [code, setCode] = useState(field?.code || '');
  const [label, setLabel] = useState(field?.label || '');
  const [helpText, setHelpText] = useState(field?.help_text || '');
  const [type, setType] = useState(field?.type || 'text');
  const [isRequired, setIsRequired] = useState(field?.is_required ?? false);
  const [order, setOrder] = useState(field?.order ?? (section.fields_list?.length || 0));
  const [placeholder, setPlaceholder] = useState(field?.placeholder || '');
  const [defaultValue, setDefaultValue] = useState(field?.default_value || '');
  const [riskWeight, setRiskWeight] = useState(field?.risk_weight ?? 0);
  // Validations
  const [minValue, setMinValue] = useState<string>(field?.min_value?.toString() || '');
  const [maxValue, setMaxValue] = useState<string>(field?.max_value?.toString() || '');
  const [minLength, setMinLength] = useState<string>(field?.min_length?.toString() || '');
  const [maxLength, setMaxLength] = useState<string>(field?.max_length?.toString() || '');
  const [regex, setRegex] = useState(field?.regex || '');
  // Options (pour select/radio/checkbox)
  const [options, setOptions] = useState<FormOption[]>(field?.options?.slice() || []);
  const [busy, setBusy] = useState(false);

  const needsOptions = useMemo(() => TYPES_WITH_OPTIONS.includes(type), [type]);
  const needsRange = useMemo(() => TYPES_WITH_RANGE.includes(type), [type]);
  const needsLength = useMemo(() => TYPES_WITH_LENGTH.includes(type), [type]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload: any = {
        section: section.id,
        code, label, help_text: helpText, type, is_required: isRequired, order,
        placeholder, default_value: defaultValue, risk_weight: riskWeight,
      };
      if (needsRange) {
        payload.min_value = minValue ? Number(minValue) : null;
        payload.max_value = maxValue ? Number(maxValue) : null;
      }
      if (needsLength) {
        payload.min_length = minLength ? Number(minLength) : null;
        payload.max_length = maxLength ? Number(maxLength) : null;
        payload.regex = regex || '';
      }

      let savedField: FormField;
      if (isEdit) {
        const r = await api.patch(`/forms/fields/${field!.id}/`, payload);
        savedField = r.data;
      } else {
        const r = await api.post('/forms/fields/', payload);
        savedField = r.data;
      }

      // Sync des options
      if (needsOptions) {
        // Supprime les options retirées
        const existingIds = new Set(field?.options?.map((o) => o.id) || []);
        const keptIds = new Set(options.filter((o) => o.id).map((o) => o.id));
        for (const oldId of Array.from(existingIds)) {
          if (!keptIds.has(oldId)) {
            try { await api.delete(`/forms/options/${oldId}/`); } catch {}
          }
        }
        // Crée ou met à jour les options actuelles
        for (const [ix, opt] of options.entries()) {
          const opayload = {
            field: savedField.id,
            value: opt.value,
            label: opt.label,
            order: ix,
            triggers_risk: opt.triggers_risk || false,
          };
          if (opt.id) {
            await api.patch(`/forms/options/${opt.id}/`, opayload);
          } else {
            await api.post('/forms/options/', opayload);
          }
        }
      }

      toast.success(isEdit ? 'Champ mis à jour' : 'Champ créé');
      onSaved();
    } catch (e: any) { toast.error(extractApiError(e)); } finally { setBusy(false); }
  };

  const addOption = () => setOptions((o) => [...o, { id: 0, value: '', label: '', order: o.length }]);
  const removeOption = (ix: number) => setOptions((o) => o.filter((_, i) => i !== ix));
  const updateOption = (ix: number, patch: Partial<FormOption>) =>
    setOptions((o) => o.map((opt, i) => (i === ix ? { ...opt, ...patch } : opt)));

  return (
    <ModalShell title={isEdit ? `Éditer le champ : ${field!.label}` : 'Nouveau champ'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-5">
        {/* Identité */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Code *">
            <input value={code} onChange={(e) => setCode(e.target.value)} className="input-base font-mono" required placeholder="field-code" />
          </Field>
          <Field label="Type *">
            <select value={type} onChange={(e) => setType(e.target.value)} className="input-base">
              {FIELD_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Libellé *" className="sm:col-span-2">
            <input value={label} onChange={(e) => setLabel(e.target.value)} className="input-base" required placeholder="Question affichée à l'utilisateur" />
          </Field>
          <Field label="Texte d'aide" className="sm:col-span-2">
            <input value={helpText} onChange={(e) => setHelpText(e.target.value)} className="input-base" placeholder="Précision affichée sous le champ" />
          </Field>
        </div>

        {/* Comportement */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Field label="Placeholder">
            <input value={placeholder} onChange={(e) => setPlaceholder(e.target.value)} className="input-base" />
          </Field>
          <Field label="Valeur par défaut">
            <input value={defaultValue} onChange={(e) => setDefaultValue(e.target.value)} className="input-base" />
          </Field>
          <Field label="Ordre">
            <input type="number" value={order} onChange={(e) => setOrder(Number(e.target.value))} className="input-base" />
          </Field>
          <Field label="Poids dans le score (0-100)">
            <input
              type="number" min={0} max={100}
              value={riskWeight} onChange={(e) => setRiskWeight(Number(e.target.value))}
              className="input-base"
            />
          </Field>
          <label className="sm:col-span-2 inline-flex items-center gap-2 text-sm self-end pb-2">
            <input type="checkbox" checked={isRequired} onChange={(e) => setIsRequired(e.target.checked)} />
            <span><strong>Champ obligatoire</strong></span>
          </label>
        </div>

        {/* Validations conditionnelles selon le type */}
        {needsRange && (
          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Field label="Valeur min">
              <input type="number" value={minValue} onChange={(e) => setMinValue(e.target.value)} className="input-base" />
            </Field>
            <Field label="Valeur max">
              <input type="number" value={maxValue} onChange={(e) => setMaxValue(e.target.value)} className="input-base" />
            </Field>
          </div>
        )}
        {needsLength && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Field label="Longueur min">
              <input type="number" value={minLength} onChange={(e) => setMinLength(e.target.value)} className="input-base" />
            </Field>
            <Field label="Longueur max">
              <input type="number" value={maxLength} onChange={(e) => setMaxLength(e.target.value)} className="input-base" />
            </Field>
            <Field label="Regex (avancé)">
              <input value={regex} onChange={(e) => setRegex(e.target.value)} className="input-base font-mono" placeholder="^[A-Z]{3}-..." />
            </Field>
          </div>
        )}

        {/* Options (select/radio/checkbox) */}
        {needsOptions && (
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Options</span>
              <button type="button" onClick={addOption} className="text-xs text-emerald-600 hover:underline">
                + Ajouter une option
              </button>
            </div>
            {options.length === 0 && (
              <div className="text-xs text-slate-400 py-3 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                Aucune option. Ajoutez-en au moins une.
              </div>
            )}
            {options.map((opt, ix) => (
              <div key={ix} className="flex gap-2 mb-2">
                <input
                  value={opt.value}
                  onChange={(e) => updateOption(ix, { value: e.target.value })}
                  className="input-base flex-1 font-mono"
                  placeholder="valeur"
                />
                <input
                  value={opt.label}
                  onChange={(e) => updateOption(ix, { label: e.target.value })}
                  className="input-base flex-[2]"
                  placeholder="Libellé affiché"
                />
                <label className="inline-flex items-center gap-1 text-xs whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={opt.triggers_risk || false}
                    onChange={(e) => updateOption(ix, { triggers_risk: e.target.checked })}
                    title="Cocher si cette option contribue au score de risque"
                  />
                  ⚠ risque
                </label>
                <button type="button" onClick={() => removeOption(ix)} className="text-slate-400 hover:text-rose-600">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button type="button" onClick={onClose} className="btn-secondary">Annuler</button>
          <button type="submit" disabled={busy} className="btn-primary">
            {busy ? '...' : (isEdit ? 'Enregistrer' : 'Créer le champ')}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
