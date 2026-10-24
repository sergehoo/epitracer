/**
 * Logo historique « Destination Côte d'Ivoire » du portail public.
 *
 * Reprise à l'identique du lettrage d'origine (ancien en-tête public) :
 * « Destination » manuscrit (Sacramento) orange, « CÔTE D'IVOIRE » en capitales
 * vertes espacées, signature « Akwaba · Bienvenue · Welcome ». Ne pas remplacer
 * par une police générique : la police Sacramento est chargée dans globals.css.
 * « EpiTrace » reste réservé au système technique et à l'administration.
 */
const SIZES = {
  sm: { script: 'text-[1.55rem]', caps: 'text-[0.72rem]', tagline: 'text-[9px]' },
  md: { script: 'text-[2rem]', caps: 'text-[0.9rem]', tagline: 'text-[10px]' },
  lg: { script: 'text-[2.6rem]', caps: 'text-[1.1rem]', tagline: 'text-xs' },
} as const;

export function DestinationBrand({
  size = 'md',
  tagline = true,
  className = '',
}: {
  size?: keyof typeof SIZES;
  tagline?: boolean;
  className?: string;
}) {
  const s = SIZES[size];
  return (
    <span className={`inline-flex flex-col leading-none select-none ${className}`}>
      <span
        className={`font-script text-ciOrange leading-[0.85] -mb-1 drop-shadow-[0_2px_0_rgba(247,127,0,0.18)] ${s.script}`}
      >
        Destination
      </span>
      <span className={`whitespace-nowrap font-display font-extrabold uppercase tracking-[0.18em] text-ciGreen ${s.caps}`}>
        Côte d&apos;Ivoire
      </span>
      {tagline && (
        <span className={`mt-1 whitespace-nowrap italic text-slate-500 ${s.tagline}`}>
          Akwaba · Bienvenue · Welcome
        </span>
      )}
    </span>
  );
}
