/**
 * OfficialBrand — bandeau institutionnel réutilisable.
 *
 * Affiche les 3 logos officiels (MSHPCMU · Armoiries CI · INHP) +
 * la devise et l'abréviation MSHPCMU.
 */
import { cn } from '@/lib/utils';

const MSHPCMU = '/logo-min-sante-2.png';
const ARMOIRIE = '/armoirie-ci-2.png';
const INHP = '/logo-INHP.png';

interface Props {
  variant?: 'row' | 'stack' | 'compact';
  showText?: boolean;
  className?: string;
}

export function OfficialBrand({ variant = 'row', showText = true, className }: Props) {
  if (variant === 'compact') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <img src={MSHPCMU} alt="MSHPCMU" className="h-9 w-9 object-contain" />
        <img src={ARMOIRIE} alt="Armoiries CI" className="h-9 w-9 object-contain" />
        <img src={INHP} alt="INHP" className="h-9 w-auto object-contain" />
      </div>
    );
  }

  if (variant === 'stack') {
    return (
      <div className={cn('flex flex-col items-center text-center gap-2', className)}>
        <div className="flex items-center justify-center gap-4">
          <img src={MSHPCMU} alt="MSHPCMU" className="h-14 w-14 object-contain" />
          <img src={ARMOIRIE} alt="Armoiries CI" className="h-14 w-14 object-contain" />
          <img src={INHP} alt="INHP" className="h-14 w-auto object-contain" />
        </div>
        {showText && (
          <div className="mt-1 text-[10px] sm:text-xs leading-tight text-slate-600 dark:text-slate-300">
            <div className="font-bold text-ciDark dark:text-emerald-200 uppercase tracking-wide">
              République de Côte d'Ivoire
            </div>
            <div className="italic text-slate-500">Union · Discipline · Travail</div>
            <div className="font-semibold mt-0.5">
              MSHPCMU · Institut National d'Hygiène Publique
            </div>
          </div>
        )}
      </div>
    );
  }

  // row (par défaut)
  return (
    <div className={cn('flex items-center gap-4', className)}>
      <img src={MSHPCMU} alt="MSHPCMU" className="h-12 w-12 object-contain shrink-0" />
      <img src={ARMOIRIE} alt="Armoiries CI" className="h-12 w-12 object-contain shrink-0" />
      <img src={INHP} alt="INHP" className="h-10 w-auto object-contain shrink-0" />
      {showText && (
        <div className="leading-tight border-l border-slate-200 dark:border-slate-700 pl-4">
          <div className="text-[10px] uppercase tracking-widest text-slate-500">
            République de Côte d'Ivoire
          </div>
          <div className="font-display font-black text-ciDark dark:text-emerald-200">
            MSHPCMU · INHP
          </div>
          <div className="text-[10px] text-slate-500 italic">Union · Discipline · Travail</div>
        </div>
      )}
    </div>
  );
}
