'use client';

/**
 * "Mes messages" — section publique qui liste tous les check-ins
 * du voyageur sous forme de fil chronologique.
 *
 * Chaque ligne montre la date, le ressenti déclaré, les symptômes
 * éventuels, la température. Si le backend a déclenché une alerte
 * sur ce check-in, un badge rassurant l'indique.
 *
 * Affichée en dessous du cadre du pass dans /pass/[publicId].
 */

import { useEffect, useState } from 'react';
import { CheckCircle2, MessageCircle, ThermometerSun, AlertCircle, HeartHandshake } from 'lucide-react';
import { fetchFollowUpStatus, type CheckEntry } from '@/lib/companion';

const FEELING_STYLES: Record<string, { label: string; tone: string; icon: React.ReactNode }> = {
  ok: { label: 'Je vais bien', tone: 'emerald', icon: <CheckCircle2 className="h-4 w-4" /> },
  symptom: { label: 'Symptôme signalé', tone: 'amber', icon: <ThermometerSun className="h-4 w-4" /> },
  assistance: { label: 'Demande d\'assistance', tone: 'rose', icon: <HeartHandshake className="h-4 w-4" /> },
};

const TONE_BG: Record<string, string> = {
  emerald: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  amber: 'bg-amber-50 border-amber-200 text-amber-800',
  rose: 'bg-rose-50 border-rose-200 text-rose-800',
  slate: 'bg-slate-50 border-slate-200 text-slate-700',
};

const SYMPTOM_LABELS: Record<string, string> = {
  fever: 'Fièvre',
  intense_fatigue: 'Fatigue intense',
  severe_headache: 'Maux de tête',
  muscle_joint_pain: 'Douleurs musculaires',
  sore_throat_or_abdominal: 'Mal de gorge / abdominal',
  diarrhea_nausea_vomiting: 'Diarrhée / nausées',
  unexplained_bleeding: 'Saignements',
};

export function MyMessages({ publicId }: { publicId: string }) {
  const [checks, setChecks] = useState<CheckEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!publicId) return;
    fetchFollowUpStatus(publicId)
      .then((data) => setChecks(data.checks || []))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [publicId]);

  if (loading) {
    return (
      <article className="card p-6">
        <div className="animate-pulse h-24 bg-slate-100 dark:bg-slate-900 rounded-xl" />
      </article>
    );
  }

  return (
    <article className="card p-6">
      <header className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-ciOrange font-black">
            Historique
          </div>
          <h3 className="font-display text-xl font-black text-ciDark dark:text-emerald-200 mt-1">
            Mes messages au service sanitaire
          </h3>
        </div>
        <div className="text-right">
          <div className="text-2xl font-black text-ciGreen">{checks.length}</div>
          <div className="text-xs text-slate-500">check-in(s)</div>
        </div>
      </header>

      {checks.length === 0 ? (
        <div className="text-center py-10">
          <MessageCircle className="h-10 w-10 mx-auto text-slate-300 mb-3" />
          <p className="text-sm text-slate-500">
            Vous n'avez pas encore envoyé de message.
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Ouvrez l'onglet « Suivi » pour donner de vos nouvelles.
          </p>
        </div>
      ) : (
        <ol className="space-y-3">
          {checks.map((c, idx) => {
            const fStyle = c.feeling ? FEELING_STYLES[c.feeling] : null;
            const tone = fStyle?.tone || 'slate';
            const date = new Date(c.check_date).toLocaleDateString('fr-FR', {
              weekday: 'short', day: 'numeric', month: 'short',
            });
            return (
              <li
                key={`${c.check_date}-${idx}`}
                className={`p-4 rounded-xl border ${TONE_BG[tone]}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {fStyle?.icon}
                    <div>
                      <div className="text-xs uppercase tracking-wide opacity-70">
                        Jour J{c.day_index} · {date}
                      </div>
                      <div className="font-semibold text-sm">
                        {fStyle?.label || 'Check-in'}
                      </div>
                    </div>
                  </div>
                  {c.temperature_celsius != null && (
                    <div className="text-xs font-bold tabular-nums">
                      {c.temperature_celsius}°C
                    </div>
                  )}
                </div>

                {c.positive_symptoms && c.positive_symptoms.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {c.positive_symptoms.map((s) => (
                      <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-white/70 dark:bg-slate-950/30 font-medium">
                        {SYMPTOM_LABELS[s] || s}
                      </span>
                    ))}
                  </div>
                )}

                {c.notes && (
                  <p className="mt-2 text-xs italic opacity-80 line-clamp-2">
                    « {c.notes} »
                  </p>
                )}

                {c.alert_raised && (
                  <div className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold">
                    <AlertCircle className="h-3 w-3" />
                    Une équipe sanitaire a été notifiée — vous serez recontacté(e).
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </article>
  );
}
