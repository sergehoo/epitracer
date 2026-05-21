import { InhpHeader } from '@/components/ui/InhpHeader';
import { InhpFooter } from '@/components/ui/InhpFooter';

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-white text-slate-900 overflow-x-hidden">
      <InhpHeader variant="public" />
      {/* pt-20 = compense la hauteur du header fixed (h-16 + padding) */}
      <main className="flex-1 pt-20">{children}</main>
      <InhpFooter />
    </div>
  );
}
