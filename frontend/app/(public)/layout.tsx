import { InhpHeader } from '@/components/ui/InhpHeader';
import { InhpFooter } from '@/components/ui/InhpFooter';
import { ForceLightTheme } from '@/components/layout/ForceLightTheme';

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    // `data-theme="light"` + `light` class : double sécurité côté SSR pour
    // que Tailwind ne déclenche pas les variantes dark: avant hydration.
    // ForceLightTheme prend le relais côté client via next-themes.
    <div
      data-theme="light"
      className="light min-h-screen flex flex-col bg-white text-slate-900 overflow-x-hidden"
    >
      <ForceLightTheme />
      <InhpHeader variant="public" />
      {/* pt-20 = compense la hauteur du header fixed (h-16 + padding) */}
      <main className="flex-1 pt-20">{children}</main>
      <InhpFooter />
    </div>
  );
}
