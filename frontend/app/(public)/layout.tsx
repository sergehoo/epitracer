import { InhpHeader } from '@/components/ui/InhpHeader';
import { InhpFooter } from '@/components/ui/InhpFooter';

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <InhpHeader variant="public" />
      <main className="flex-1">{children}</main>
      <InhpFooter />
    </div>
  );
}
