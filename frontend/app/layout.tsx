import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: {
    default: 'EpiTravel — Portail National de Surveillance des Voyageurs',
    template: '%s — EpiTravel',
  },
  description:
    "Plateforme nationale de surveillance épidémiologique des voyageurs entrant en Côte d'Ivoire. Ministère de la Santé · INHP.",
  applicationName: 'EpiTravel',
  authors: [{ name: "Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle" }],
  keywords: ['Ebola', 'INHP', 'Côte d\'Ivoire', 'surveillance sanitaire', 'pass sanitaire'],
  formatDetection: { telephone: true, email: true },
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
      </body>
    </html>
  );
}
