import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function Section({
  title, description, children, eyebrow, className,
}: {
  title?: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('container py-12 lg:py-16', className)}>
      {(eyebrow || title || description) && (
        <header className="mb-8 max-w-3xl">
          {eyebrow && <div className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400 font-semibold">{eyebrow}</div>}
          {title && <h2 className="mt-2 font-display text-3xl lg:text-4xl font-bold tracking-tight">{title}</h2>}
          {description && <p className="mt-3 text-slate-600 dark:text-slate-300">{description}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
