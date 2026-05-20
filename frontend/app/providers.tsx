'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { Toaster } from 'react-hot-toast';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
        },
      }),
  );
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={qc}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            className: '!bg-slate-900 !text-white dark:!bg-slate-100 dark:!text-slate-900',
            success: { iconTheme: { primary: '#10B981', secondary: 'white' } },
            error: { iconTheme: { primary: '#EF4444', secondary: 'white' } },
          }}
        />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
