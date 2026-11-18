import { ALERT_LEVEL_STYLE } from '@/lib/portal';
import type { PublicAlertLevel } from '@/types/portal';

/** Badge du niveau d'alerte public (Veille → Urgence sanitaire). */
export function AlertLevelBadge({
  level, label, locale = 'fr',
}: { level: PublicAlertLevel; label?: string; locale?: 'fr' | 'en' }) {
  const style = ALERT_LEVEL_STYLE[level] ?? ALERT_LEVEL_STYLE.normal;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-black uppercase tracking-wide ring-1 ring-inset ${style.className}`}
    >
      <span className="sr-only">{locale === 'en' ? 'Alert level: ' : 'Niveau d\'alerte : '}</span>
      {label || style.label}
    </span>
  );
}
