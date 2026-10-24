import { InhpHeader } from '@/components/ui/InhpHeader';
import { InhpFooter } from '@/components/ui/InhpFooter';
import { ForceLightTheme } from '@/components/layout/ForceLightTheme';
import { PublicShell } from '@/components/public/PublicShell';

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
      <PublicShell>
        <InhpHeader variant="public" />
        {/* pt = hauteur du header fixe (bande tricolore 4px + barre 64px) */}
        <main id="contenu" tabIndex={-1} className="flex-1 pt-[4.25rem] focus:outline-none">
          {children}
        </main>
        <InhpFooter />
      </PublicShell>
    </div>
  );
}
