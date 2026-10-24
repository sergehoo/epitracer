import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import { PwaRegister } from '@/components/public/PwaRegister';
import { VisitTracker } from '@/components/public/VisitTracker';
import '../styles/globals.css';

const PUBLIC_HOST = process.env.NEXT_PUBLIC_PUBLIC_HOST;

export const metadata: Metadata = {
  metadataBase: new URL(PUBLIC_HOST ? `https://${PUBLIC_HOST}` : 'http://localhost:3000'),
  title: {
    default: 'EpiTrace CI — MSHPCMU · INHP',
    template: '%s — EpiTrace CI',
  },
  description:
    "Dispositif national d'information, de prévention et d'accompagnement sanitaire des voyageurs en Côte d'Ivoire : maladies sous surveillance, alertes sanitaires, pass sanitaire et suivi. MSHPCMU · Institut National d'Hygiène Publique (INHP).",
  applicationName: 'EpiTrace CI',
  authors: [{ name: "MSHPCMU - Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle" }],
  keywords: [
    'MSHPCMU', 'INHP', "Côte d'Ivoire", 'veille sanitaire', 'maladies sous surveillance',
    'alertes sanitaires', 'voyageurs', 'pass sanitaire', 'Ebola', 'Mpox', 'choléra', 'fièvre jaune',
  ],
  formatDetection: { telephone: true, email: true },
  // Administration (EpiTrace) ; le portail public surcharge ce manifeste
  // dans app/(public)/layout.tsx (« Destination Côte d'Ivoire »).
  manifest: '/admin.webmanifest',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'EpiTrace CI',
  },
  icons: {
    icon: [
      { url: '/logo-min-sante-2.png', type: 'image/png' },
    ],
    shortcut: [{ url: '/logo-min-sante-2.png' }],
    apple: [{ url: '/logo-min-sante-2.png' }],
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0B1220' },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 antialiased">
        <Providers>{children}</Providers>
        <PwaRegister />
        <VisitTracker />
      </body>
    </html>
  );
}
