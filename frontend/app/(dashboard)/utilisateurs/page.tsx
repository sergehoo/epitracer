'use client';

import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

// =========================================================================
// Types
// =========================================================================
interface UserRoleSummary {
  code: string;
  name: string;
}
interface User {
  id: number;
  uuid: string;
  email: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  job_title?: string;
  is_active: boolean;
  is_locked: boolean;
  mfa_enabled: boolean;
  mfa_enforced?: boolean;
  last_login: string | null;
  date_joined?: string;
  roles: UserRoleSummary[];
}
interface Role {
  id: number;
  code: string;
  name: string;
  description: string;
  is_system: boolean;
}
interface Organization {
  id: number;
  uuid: string;
  code: string;
  name: string;
  type: string;
  parent: number | null;
}
interface RoleAssignment {
  id: number;
  user: number;
  role: number;
  role_code?: string;
  role_name?: string;
  organization: number | null;
  organization_name?: string | null;
  is_active: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
}

// =========================================================================
// Page principale
// =========================================================================
export default function UtilisateursPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // filtres
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive' | 'locked'>('all');
  const [filterRole, setFilterRole] = useState<string>('');

  // modals
  const [showCreate, setShowCreate] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [managingRoles, setManagingRoles] = useState<User | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    danger?: boolean;
    onConfirm: () => Promise<void> | void;
  } | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [u, r, o] = await Promise.all([
        api.get('/auth/users/?page_size=200'),
        api.get('/auth/roles/?page_size=50'),
        api.get('/auth/organizations/?page_size=100'),
      ]);
      setUsers(u.data.results || u.data);
      setRoles(r.data.results || r.data);
      setOrgs(o.data.results || o.data);
      setErr(null);
    } catch (e: any) {
      setErr(extractApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    return users.filter((u) => {
      if (filterStatus === 'active' && (!u.is_active || u.is_locked)) return false;
      if (filterStatus === 'inactive' && u.is_active) return false;
      if (filterStatus === 'locked' && !u.is_locked) return false;
      if (filterRole && !u.roles?.some((r) => r.code === filterRole)) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !u.email?.toLowerCase().includes(q) &&
          !u.full_name?.toLowerCase().includes(q) &&
          !u.phone?.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [users, search, filterStatus, filterRole]);

  const kpis = useMemo(() => {
    const total = users.length;
    const actifs = users.filter((u) => u.is_active && !u.is_locked).length;
    const verrouilles = users.filter((u) => u.is_locked).length;
    const mfa = users.filter((u) => u.mfa_enabled).length;
    return { total, actifs, verrouilles, mfa };
  }, [users]);

  // Actions
  const doLock = (u: User) =>
    setConfirmDialog({
      title: 'Verrouiller le compte',
      message: `Le compte ${u.email} ne pourra plus se connecter tant qu'il n'aura pas été déverrouillé. Continuer ?`,
      confirmLabel: 'Verrouiller',
      danger: true,
      onConfirm: async () => {
        await api.post(`/auth/users/${u.id}/lock/`);
        toast.success('Compte verrouillé');
        refresh();
      },
    });

  const doUnlock = (u: User) =>
    setConfirmDialog({
      title: 'Déverrouiller le compte',
      message: `Réactiver l'accès du compte ${u.email} ?`,
      confirmLabel: 'Déverrouiller',
      onConfirm: async () => {
        await api.post(`/auth/users/${u.id}/unlock/`);
        toast.success('Compte déverrouillé');
        refresh();
      },
    });

  const doResetPassword = (u: User) =>
    setConfirmDialog({
      title: 'Réinitialiser le mot de passe',
      message: `Un mot de passe temporaire sera généré pour ${u.email}. Il devra le changer à la prochaine connexion. Continuer ?`,
      confirmLabel: 'Réinitialiser',
      onConfirm: async () => {
        const r = await api.post(`/auth/users/${u.id}/reset_password/`);
        const tmp = r.data?.temporary_password || r.data?.password;
        if (tmp) {
          await navigator.clipboard.writeText(tmp).catch(() => {});
          toast.success(`Mot de passe temporaire copié : ${tmp}`, { duration: 8000 });
        } else {
          toast.success('Mot de passe réinitialisé');
        }
        refresh();
      },
    });

  const doDelete = (u: User) =>
    setConfirmDialog({
      title: u.is_active ? 'Désactiver le compte' : 'Réactiver le compte',
      message: u.is_active
        ? `Le compte ${u.email} sera désactivé (soft delete). Toutes ses traces d'audit sont conservées et il pourra être réactivé plus tard. Continuer ?`
        : `Réactiver le compte ${u.email} ?`,
      confirmLabel: u.is_active ? 'Désactiver' : 'Réactiver',
      danger: u.is_active,
      onConfirm: async () => {
        await api.patch(`/auth/users/${u.id}/`, { is_active: !u.is_active });
        toast.success(u.is_active ? 'Compte désactivé' : 'Compte réactivé');
        refresh();
      },
    });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Utilisateurs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Comptes professionnels (MSHPCMU, INHP, districts, points d'entrée, agents).
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-orange px-4 py-2 text-sm font-medium text-white shadow hover:bg-brand-orange/90 transition"
        >
          <span>＋</span> Nouvel utilisateur
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total comptes" value={kpis.total} />
        <KpiCard label="Actifs" value={kpis.actifs} tone="success" />
        <KpiCard label="Verrouillés" value={kpis.verrouilles} tone={kpis.verrouilles > 0 ? 'danger' : 'neutral'} />
        <KpiCard label="MFA activée" value={kpis.mfa} tone="info" />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">Recherche</label>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Email, nom, téléphone..."
            className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Statut</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as any)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="all">Tous</option>
            <option value="active">Actifs</option>
            <option value="inactive">Inactifs</option>
            <option value="locked">Verrouillés</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Rôle</label>
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="">Tous</option>
            {roles.map((r) => (
              <option key={r.code} value={r.code}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto text-xs text-slate-500 self-end">
          {filtered.length} sur {users.length} utilisateurs
        </div>
      </div>

      {/* Erreur */}
      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Nom</th>
                <th className="px-4 py-3 text-left">Rôles</th>
                <th className="px-4 py-3 text-left">MFA</th>
                <th className="px-4 py-3 text-left">Statut</th>
                <th className="px-4 py-3 text-left">Dernière connexion</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-400">
                    Chargement...
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-400">
                    {users.length === 0 ? 'Aucun utilisateur. Créez le premier compte.' : 'Aucun résultat avec ces filtres.'}
                  </td>
                </tr>
              )}
              {!loading &&
                filtered.map((u) => (
                  <tr key={u.uuid} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-medium">{u.email}</td>
                    <td className="px-4 py-3">{u.full_name || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.roles?.length ? (
                          u.roles.map((r) => (
                            <span
                              key={r.code}
                              className="inline-block rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-700 dark:text-slate-300"
                              title={r.name}
                            >
                              {r.code}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {u.mfa_enabled ? <span className="badge-low">Activée</span> : <span className="badge-moderate">Désactivée</span>}
                    </td>
                    <td className="px-4 py-3">
                      {u.is_locked ? (
                        <span className="badge-high">Verrouillé</span>
                      ) : u.is_active ? (
                        <span className="badge-low">Actif</span>
                      ) : (
                        <span className="badge-moderate">Inactif</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{formatDateTime(u.last_login)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <ActionButton title="Éditer" onClick={() => setEditingUser(u)}>
                          ✏️
                        </ActionButton>
                        <ActionButton title="Rôles & permissions" onClick={() => setManagingRoles(u)}>
                          🛡️
                        </ActionButton>
                        <ActionButton title="Réinitialiser mot de passe" onClick={() => doResetPassword(u)}>
                          🔑
                        </ActionButton>
                        {u.is_locked ? (
                          <ActionButton title="Déverrouiller" onClick={() => doUnlock(u)}>
                            🔓
                          </ActionButton>
                        ) : (
                          <ActionButton title="Verrouiller" onClick={() => doLock(u)}>
                            🔒
                          </ActionButton>
                        )}
                        <ActionButton
                          title={u.is_active ? 'Désactiver' : 'Réactiver'}
                          danger={u.is_active}
                          onClick={() => doDelete(u)}
                        >
                          {u.is_active ? '🗑️' : '♻️'}
                        </ActionButton>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      {showCreate && (
        <UserFormModal
          user={null}
          roles={roles}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            refresh();
          }}
        />
      )}
      {editingUser && (
        <UserFormModal
          user={editingUser}
          roles={roles}
          onClose={() => setEditingUser(null)}
          onSaved={() => {
            setEditingUser(null);
            refresh();
          }}
        />
      )}
      {managingRoles && (
        <UserRolesModal
          user={managingRoles}
          roles={roles}
          orgs={orgs}
          onClose={() => setManagingRoles(null)}
          onChange={() => refresh()}
        />
      )}
      {confirmDialog && (
        <ConfirmDialog
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmLabel={confirmDialog.confirmLabel}
          danger={confirmDialog.danger}
          onConfirm={async () => {
            try {
              await confirmDialog.onConfirm();
            } catch (e: any) {
              toast.error(extractApiError(e));
            } finally {
              setConfirmDialog(null);
            }
          }}
          onClose={() => setConfirmDialog(null)}
        />
      )}
    </div>
  );
}

// =========================================================================
// Sous-composants
// =========================================================================

function KpiCard({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: number | string;
  tone?: 'neutral' | 'success' | 'danger' | 'info';
}) {
  const toneClass =
    tone === 'success'
      ? 'text-emerald-600'
      : tone === 'danger'
      ? 'text-rose-600'
      : tone === 'info'
      ? 'text-sky-600'
      : 'text-slate-900 dark:text-slate-100';
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-2 font-display text-3xl font-bold ${toneClass}`}>{value}</div>
    </div>
  );
}

function ActionButton({
  children,
  title,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
        danger ? 'hover:bg-rose-50 hover:text-rose-600' : ''
      }`}
    >
      {children}
    </button>
  );
}

// -------------------------------------------------------------------------
// Modal création / édition utilisateur
// -------------------------------------------------------------------------
function UserFormModal({
  user,
  roles,
  onClose,
  onSaved,
}: {
  user: User | null;
  roles: Role[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!user;
  const [email, setEmail] = useState(user?.email || '');
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [jobTitle, setJobTitle] = useState(user?.job_title || '');
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [mfaEnforced, setMfaEnforced] = useState(user?.mfa_enforced ?? false);
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user?.roles?.map((r) => r.code) || []);
  const [submitting, setSubmitting] = useState(false);
  // Erreurs détaillées par champ retournées par le backend (DRF format)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const toggleRole = (code: string) => {
    setSelectedRoles((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    try {
      // Nettoyage défensif : on évite d'envoyer des champs vides qui pourraient
      // déclencher la validation côté serveur (ex: phone "" rejeté par regex).
      const payload: any = {
        email: email.trim(),
        is_active: isActive,
      };
      if (firstName.trim()) payload.first_name = firstName.trim();
      if (lastName.trim()) payload.last_name = lastName.trim();
      if (phone.trim()) payload.phone = phone.trim();
      if (jobTitle.trim()) payload.job_title = jobTitle.trim();
      if (mfaEnforced) payload.mfa_enforced = true;
      if (!isEdit) {
        payload.role_codes = selectedRoles;
      }

      if (isEdit) {
        await api.patch(`/auth/users/${user!.id}/`, payload);
        toast.success('Utilisateur mis à jour');
      } else {
        const r = await api.post('/auth/users/', payload);
        const tmp = r.data?.temporary_password || r.data?.password;
        if (tmp) {
          await navigator.clipboard.writeText(tmp).catch(() => {});
          toast.success(`Compte créé. Mot de passe temporaire copié : ${tmp}`, { duration: 12000 });
        } else {
          toast.success('Utilisateur créé');
        }
      }
      onSaved();
    } catch (e: any) {
      // Récupération des erreurs DRF par champ pour les afficher en place.
      const raw = e?.response?.data;
      if (raw && typeof raw === 'object' && !raw.detail && !raw.error) {
        const errs: Record<string, string[]> = {};
        for (const [k, v] of Object.entries(raw)) {
          errs[k] = Array.isArray(v) ? (v as any[]).map(String) : [String(v)];
        }
        setFieldErrors(errs);
      }
      toast.error(extractApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalShell title={isEdit ? `Éditer : ${user!.email}` : 'Créer un utilisateur'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        {/* Bloc d'erreurs serveur (validation DRF par champ) */}
        {Object.keys(fieldErrors).length > 0 && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 dark:bg-rose-900/20 dark:border-rose-800/40 p-3 text-xs">
            <div className="font-bold text-rose-700 dark:text-rose-300 mb-1">
              Le serveur a refusé la création :
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-rose-700 dark:text-rose-300">
              {Object.entries(fieldErrors).map(([k, msgs]) => (
                <li key={k}>
                  <strong>{k}</strong> : {msgs.join(' · ')}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Email *">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isEdit}
              className={`input-base ${fieldErrors.email ? 'border-rose-400 ring-rose-200' : ''}`}
            />
            {fieldErrors.email && (
              <p className="text-[11px] text-rose-600 mt-1">{fieldErrors.email.join(' · ')}</p>
            )}
          </Field>
          <Field label="Téléphone">
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+225..."
              className={`input-base ${fieldErrors.phone ? 'border-rose-400 ring-rose-200' : ''}`}
            />
            {fieldErrors.phone && (
              <p className="text-[11px] text-rose-600 mt-1">{fieldErrors.phone.join(' · ')}</p>
            )}
          </Field>
          <Field label="Prénom">
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className="input-base" />
          </Field>
          <Field label="Nom">
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} className="input-base" />
          </Field>
          <Field label="Fonction" className="sm:col-span-2">
            <input
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="Ex: Coordonnateur INHP — Surveillance épidémiologique"
              className="input-base"
            />
          </Field>
        </div>

        {!isEdit && (
          <div>
            <div className="block text-xs font-medium text-slate-500 mb-2">Rôles initiaux (sans organisation)</div>
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => (
                <label
                  key={r.code}
                  className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs cursor-pointer transition ${
                    selectedRoles.includes(r.code)
                      ? 'border-brand-orange bg-orange-50 dark:bg-orange-950/30 text-brand-orange'
                      : 'border-slate-200 dark:border-slate-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={selectedRoles.includes(r.code)}
                    onChange={() => toggleRole(r.code)}
                  />
                  <span className="font-medium">{r.code}</span>
                  <span className="text-slate-500">— {r.name}</span>
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Pour affecter une organisation à un rôle, ouvrir « Rôles & permissions » après création.
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-4 border-t border-slate-100 dark:border-slate-800 pt-4">
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            <span>Compte actif</span>
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={mfaEnforced} onChange={(e) => setMfaEnforced(e.target.checked)} />
            <span>Forcer la MFA à la prochaine connexion</span>
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button type="button" onClick={onClose} className="btn-secondary">
            Annuler
          </button>
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer'}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

// -------------------------------------------------------------------------
// Modal gestion rôles et permissions par user
// -------------------------------------------------------------------------
function UserRolesModal({
  user,
  roles,
  orgs,
  onClose,
  onChange,
}: {
  user: User;
  roles: Role[];
  orgs: Organization[];
  onClose: () => void;
  onChange: () => void;
}) {
  const [assignments, setAssignments] = useState<RoleAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newRoleId, setNewRoleId] = useState<number | ''>('');
  const [newOrgId, setNewOrgId] = useState<number | ''>('');
  const [validTo, setValidTo] = useState<string>('');
  const [adding, setAdding] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/auth/role-assignments/?user=${user.id}&page_size=100`);
      setAssignments(r.data.results || r.data);
    } catch (e: any) {
      toast.error(extractApiError(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    refresh();
  }, [user.id]);

  const add = async () => {
    if (!newRoleId) {
      toast.error('Sélectionnez un rôle');
      return;
    }
    setAdding(true);
    try {
      await api.post('/auth/role-assignments/', {
        user: user.id,
        role: newRoleId,
        organization: newOrgId || null,
        valid_to: validTo || null,
        is_active: true,
      });
      toast.success('Rôle affecté');
      setNewRoleId('');
      setNewOrgId('');
      setValidTo('');
      await refresh();
      onChange();
    } catch (e: any) {
      toast.error(extractApiError(e));
    } finally {
      setAdding(false);
    }
  };

  const toggle = async (a: RoleAssignment) => {
    try {
      await api.patch(`/auth/role-assignments/${a.id}/`, { is_active: !a.is_active });
      toast.success(a.is_active ? 'Rôle suspendu' : 'Rôle réactivé');
      await refresh();
      onChange();
    } catch (e: any) {
      toast.error(extractApiError(e));
    }
  };

  const remove = async (a: RoleAssignment) => {
    if (!confirm(`Retirer définitivement le rôle ${a.role_code || ''} ?`)) return;
    try {
      await api.delete(`/auth/role-assignments/${a.id}/`);
      toast.success('Rôle retiré');
      await refresh();
      onChange();
    } catch (e: any) {
      toast.error(extractApiError(e));
    }
  };

  return (
    <ModalShell title={`Rôles & permissions — ${user.email}`} onClose={onClose} wide>
      <div className="space-y-5">
        {/* Liste des affectations existantes */}
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
            Rôles actifs ({assignments.length})
          </div>
          {loading ? (
            <div className="text-sm text-slate-400 py-4">Chargement...</div>
          ) : assignments.length === 0 ? (
            <div className="text-sm text-slate-400 py-4 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg text-center">
              Aucun rôle affecté. Utilisez le formulaire ci-dessous pour en ajouter un.
            </div>
          ) : (
            <div className="space-y-2">
              {assignments.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3"
                >
                  <div className="flex-1 min-w-[200px]">
                    <div className="font-medium text-sm">
                      {a.role_code || `Rôle #${a.role}`}{' '}
                      {a.role_name && <span className="text-slate-400 font-normal">— {a.role_name}</span>}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      Organisation : {a.organization_name || (a.organization ? `#${a.organization}` : 'Aucune (national)')}
                      {a.valid_to && (
                        <>
                          {' '}
                          • Expire le {formatDateTime(a.valid_to)}
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {a.is_active ? (
                      <span className="badge-low">Actif</span>
                    ) : (
                      <span className="badge-moderate">Suspendu</span>
                    )}
                    <button onClick={() => toggle(a)} className="text-xs text-slate-600 hover:text-brand-orange">
                      {a.is_active ? 'Suspendre' : 'Réactiver'}
                    </button>
                    <button onClick={() => remove(a)} className="text-xs text-rose-600 hover:underline">
                      Retirer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Ajout d'un nouveau rôle */}
        <div className="border-t border-slate-100 dark:border-slate-800 pt-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Affecter un nouveau rôle</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Field label="Rôle *">
              <select value={newRoleId} onChange={(e) => setNewRoleId(e.target.value ? Number(e.target.value) : '')} className="input-base">
                <option value="">— Sélectionner —</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.code} — {r.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Organisation">
              <select value={newOrgId} onChange={(e) => setNewOrgId(e.target.value ? Number(e.target.value) : '')} className="input-base">
                <option value="">— Aucune (national) —</option>
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({o.type})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Expire le (optionnel)">
              <input type="datetime-local" value={validTo} onChange={(e) => setValidTo(e.target.value)} className="input-base" />
            </Field>
          </div>
          <div className="mt-3 flex justify-end">
            <button onClick={add} disabled={adding || !newRoleId} className="btn-primary">
              {adding ? 'Ajout...' : 'Ajouter le rôle'}
            </button>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800">
          <button onClick={onClose} className="btn-secondary">
            Fermer
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

// -------------------------------------------------------------------------
// Confirm dialog
// -------------------------------------------------------------------------
function ConfirmDialog({
  title,
  message,
  confirmLabel,
  danger,
  onConfirm,
  onClose,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void | Promise<void>;
  onClose: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  return (
    <ModalShell title={title} onClose={onClose}>
      <p className="text-sm text-slate-600 dark:text-slate-300">{message}</p>
      <div className="flex justify-end gap-2 pt-6">
        <button onClick={onClose} className="btn-secondary">
          Annuler
        </button>
        <button
          onClick={async () => {
            setSubmitting(true);
            try {
              await onConfirm();
            } finally {
              setSubmitting(false);
            }
          }}
          disabled={submitting}
          className={danger ? 'btn-danger' : 'btn-primary'}
        >
          {submitting ? '...' : confirmLabel}
        </button>
      </div>
    </ModalShell>
  );
}

// -------------------------------------------------------------------------
// Helpers UI
// -------------------------------------------------------------------------
function ModalShell({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div
        className={`bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full ${wide ? 'max-w-3xl' : 'max-w-md'} mt-8 mb-8`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-xl leading-none">
            ×
          </button>
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
