'use client';

/**
 * AssignAgentModal — Assignation d'un suivi à un agent / district / équipe.
 *
 * POST /api/v1/admin/followups/{travelerId}/assign-agent/
 *   { assigned_agent_id?, assigned_district_id?, assigned_team? }
 *
 * Au moins un des trois champs doit être renseigné. Les listes d'agents
 * (rôle field_agent) et de districts (HealthZone level=district) sont
 * fetchées au montage de la modale.
 */

import { useEffect, useState } from 'react';
import { X, Loader2, UserCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface UserItem {
  id: number;
  email?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
}

interface DistrictItem {
  id: number;
  name: string;
  code?: string;
}

interface Props {
  open: boolean;
  travelerId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

function userLabel(u: UserItem): string {
  if (u.full_name) return u.full_name;
  const name = `${u.first_name || ''} ${u.last_name || ''}`.trim();
  return name || u.email || `Utilisateur #${u.id}`;
}

export function AssignAgentModal({ open, travelerId, onClose, onSuccess }: Props) {
  const [agentId, setAgentId] = useState<string>('');
  const [districtId, setDistrictId] = useState<string>('');
  const [team, setTeam] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  const [agents, setAgents] = useState<UserItem[]>([]);
  const [districts, setDistricts] = useState<DistrictItem[]>([]);
  const [loadingLists, setLoadingLists] = useState(false);

  useEffect(() => {
    if (!open) return;
    setAgentId('');
    setDistrictId('');
    setTeam('');
    setSubmitting(false);

    setLoadingLists(true);
    // Fetch agents (rôle field_agent) + districts (HealthZone level=district)
    // Best-effort : si une des listes ne répond pas, on laisse le champ vide.
    Promise.allSettled([
      api.get<{ results: UserItem[] } | UserItem[]>('/users/', {
        params: { role: 'field_agent', page_size: 100 },
      }),
      api.get<{ results: DistrictItem[] } | DistrictItem[]>('/geo/health-zones/', {
        params: { level: 'district', page_size: 200 },
      }),
    ]).then(([resA, resD]) => {
      if (resA.status === 'fulfilled') {
        const data = resA.value.data;
        const list = Array.isArray(data) ? data : (data?.results ?? []);
        setAgents(list);
      }
      if (resD.status === 'fulfilled') {
        const data = resD.value.data;
        const list = Array.isArray(data) ? data : (data?.results ?? []);
        setDistricts(list);
      }
    }).finally(() => setLoadingLists(false));
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    const aid = agentId ? Number(agentId) : null;
    const did = districtId ? Number(districtId) : null;
    const teamT = team.trim();
    if (!aid && !did && !teamT) {
      toast.error('Renseignez au moins agent, district ou équipe.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/admin/followups/${travelerId}/assign-agent/`, {
        assigned_agent_id: aid,
        assigned_district_id: did,
        assigned_team: teamT,
      });
      toast.success('Assignation mise à jour.');
      onSuccess?.();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mt-16"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-emerald-600" /> Assigner agent
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-xs text-slate-500">
            Renseignez au moins un champ (agent, district ou équipe libre).
            Les autres restent inchangés s'ils sont laissés vides.
          </p>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Agent de terrain
            </label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              disabled={loadingLists}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              <option value="">— Aucun changement —</option>
              {agents.map((a) => (
                <option key={a.id} value={String(a.id)}>{userLabel(a)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              District sanitaire
            </label>
            <select
              value={districtId}
              onChange={(e) => setDistrictId(e.target.value)}
              disabled={loadingLists}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              <option value="">— Aucun changement —</option>
              {districts.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.name}{d.code ? ` (${d.code})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Équipe (texte libre)
            </label>
            <input
              type="text"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              maxLength={120}
              placeholder="Ex. Équipe Cocody-Plateau"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            />
          </div>

          {loadingLists && (
            <div className="text-xs text-slate-400 inline-flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Chargement des listes…
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-bold hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Assignation…</>
            ) : (
              'Assigner'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AssignAgentModal;
