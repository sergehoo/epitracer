/**
 * Crédit AfriqConsulting — bandeau partagé entre footers public et admin.
 *
 * @param variant "dark" pour fond sombre (footer public), "light" pour
 *                 admin (fond clair). Le texte et le logo s'adaptent.
 */
type Variant = 'dark' | 'light';

export function AfriqConsultingCredit({
  variant = 'light',
}: {
  variant?: Variant;
}) {
  const isDark = variant === 'dark';
  return (
    <div
      className={`flex items-center justify-center gap-2 text-xs ${
        isDark ? 'text-emerald-100/70' : 'text-slate-500 dark:text-slate-400'
      }`}
    >
      <span>© {new Date().getFullYear()} — Réalisé par</span>
      <a
        href="https://afriqconsulting.com"
        target="_blank"
        rel="noreferrer"
        className={`inline-flex items-center gap-1.5 font-semibold transition hover:opacity-80 ${
          isDark ? 'text-white' : 'text-slate-700 dark:text-slate-200'
        }`}
      >
        <img
          src="/afriqconusultinglogo.png"
          alt="AfriqConsulting"
          className={`h-5 w-auto object-contain ${
            isDark ? 'brightness-0 invert' : ''
          }`}
        />
        <span>AfriqConsulting</span>
      </a>
    </div>
  );
}
