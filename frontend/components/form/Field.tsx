import { ReactNode } from 'react';

export function FieldRow({ children }: { children: ReactNode }) {
  return <div className="grid md:grid-cols-2 gap-4">{children}</div>;
}

export function FieldGroup({
  label, required, error, help, children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  help?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="field-label">
        {label} {required && <span className="text-rose-600">*</span>}
      </label>
      {children}
      {help && !error && <p className="field-help">{help}</p>}
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}

export function YesNo({
  value, onChange, name,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  name: string;
}) {
  return (
    <div className="inline-flex rounded-xl border border-slate-300 dark:border-slate-700 p-1 bg-white dark:bg-slate-950">
      <button
        type="button"
        onClick={() => onChange(true)}
        className={`px-4 py-2 text-sm rounded-lg font-semibold transition ${value ? 'bg-rose-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:bg-rose-50 dark:hover:bg-rose-950/40'}`}
        aria-pressed={value}
        data-name={name}
      >OUI</button>
      <button
        type="button"
        onClick={() => onChange(false)}
        className={`px-4 py-2 text-sm rounded-lg font-semibold transition ${!value ? 'bg-emerald-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/40'}`}
        aria-pressed={!value}
      >NON</button>
    </div>
  );
}
