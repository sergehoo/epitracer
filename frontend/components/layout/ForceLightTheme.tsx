'use client';

import { useTheme } from 'next-themes';
import { useEffect } from 'react';

/**
 * Force le mode light sur l'espace public (landing, formulaire voyageur, pass).
 *
 * Pourquoi : la landing publique n'a pas été designée avec des variantes
 * dark: Tailwind. Quand l'utilisateur visite avec un OS en dark mode, le
 * ThemeProvider racine ajoute la classe `dark` sur <html> ce qui fait
 * basculer les composants shadcn en dark alors que le reste reste light
 * → contraste cassé partout.
 *
 * Sur les sites institutionnels santé (who.int, vaccinepass.gov, etc.),
 * le standard est de rester en light pour préserver l'identité visuelle
 * officielle et la lisibilité des codes couleur (orange/vert CI).
 *
 * À monter au plus haut du layout public — pas besoin de wrapper, juste un
 * effet de bord qui se déclenche au mount et reste actif tant que l'user
 * est dans cette zone. Si l'utilisateur navigue vers /admin, le composant
 * sera démonté et l'ancien thème système reprendra.
 */
export function ForceLightTheme() {
  const { theme, setTheme, systemTheme } = useTheme();

  useEffect(() => {
    if (theme !== 'light') {
      setTheme('light');
    }
    // Si la classe `dark` traîne encore sur <html> (cas du SSR initial avant
    // hydration de next-themes), on la retire défensivement.
    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Au démontage (navigation vers l'admin), on remet le thème système.
  useEffect(() => {
    return () => {
      if (systemTheme) {
        setTheme('system');
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
