import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import { PwaRegister } from '@/components/public/PwaRegister';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: {
    default: 'EpiTrace CI — MSHPCMU · INHP',
    template: '%s — EpiTrace CI',
  },
  description:
    "Plateforme nationale de surveillance épidémiologique des voyageurs entrant en Côte d'Ivoire. MSHPCMU · Institut National d'Hygiène Publique (INHP).",
  applicationName: 'EpiTrace CI',
  authors: [{ name: "MSHPCMU - Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle" }],
  keywords: ['Ebola', 'MSHPCMU', 'INHP', "Côte d'Ivoire", 'surveillance sanitaire', 'pass sanitaire'],
  formatDetection: { telephone: true, email: true },
  manifest: '/manifest.webmanifest',
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
      </body>
    </html>
  );
}
