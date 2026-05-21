'use client';

import { useEffect, useState } from 'react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface U {
  id: number; uuid: string; email: string; full_name: string;
  is_active: boolean; is_locked: boolean; mfa_enabled: boolean;
  last_login: string | null;
  roles: { code: string; name: string }[];
}

export default function UtilisateursPage() {
  const [items, setItems] = useState<U[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.get('/auth/users/?page_size=50')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Utilisateurs</h1>
        <p className="text-sm text-slate-500 mt-1">Comptes professionnels (MSHPCMU, INHP, districts, points d'entrée, agents).</p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
            <tr><th className="px-4 py-3 text-left">Email</th><th className="text-left">Nom</th><th className="text-left">Rôles</th><th className="text-left">MFA</th><th className="text-left">Statut</th><th className="text-left">Dernière connexion</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">Aucun utilisateur.</td></tr>}
            {items.map((u) => (
              <tr key={u.uuid}>
                <td className="px-4 py-3 font-medium">{u.email}</td>
                <td className="px-4 py-3">{u.full_name}</td>
                <td className="px-4 py-3 text-xs">{u.roles?.map((r) => r.code).join(', ') || '—'}</td>
                <td className="px-4 py-3">{u.mfa_enabled ? <span className="badge-low">Activée</span> : <span className="badge-moderate">Désactivée</span>}</td>
                <td className="px-4 py-3">{u.is_locked ? <span className="badge-high">Verrouillé</span> : (u.is_active ? <span className="badge-low">Actif</span> : <span className="badge-moderate">Inactif</span>)}</td>
                <td className="px-4 py-3 text-slate-500">{formatDateTime(u.last_login)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
