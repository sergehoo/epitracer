'use client';

import { useEffect } from 'react';

/**
 * useEdgeSwipe — Détecte un swipe horizontal depuis le bord de l'écran.
 *
 * Usage typique : ouvrir un drawer mobile en glissant depuis le bord gauche.
 * Ignoré sur écrans desktop (≥ lg). N'interfère pas avec les scrolls
 * verticaux (le swipe doit être nettement horizontal).
 *
 * @param onSwipeRight   Callback déclenché si swipe right depuis le bord gauche
 * @param onSwipeLeft    Callback déclenché si swipe left depuis le bord droit
 * @param enabled        Si false → écoute désactivée (pour fermer pendant un drag)
 *
 * Paramètres tactiles :
 *   - Zone de détection : 24 px depuis le bord
 *   - Seuil de déclenchement : 80 px de déplacement horizontal
 *   - Tolérance verticale : 60 px (au-delà → on considère que c'est un scroll)
 */
export function useEdgeSwipe({
  onSwipeRight,
  onSwipeLeft,
  enabled = true,
}: {
  onSwipeRight?: () => void;
  onSwipeLeft?: () => void;
  enabled?: boolean;
}) {
  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    const EDGE_WIDTH = 24;        // px depuis le bord
    const THRESHOLD = 80;         // px de swipe minimum
    const MAX_VERTICAL = 60;      // px de tolérance verticale

    let startX = 0;
    let startY = 0;
    let startFromLeftEdge = false;
    let startFromRightEdge = false;

    const onTouchStart = (e: TouchEvent) => {
      const t = e.touches[0];
      if (!t) return;
      startX = t.clientX;
      startY = t.clientY;
      startFromLeftEdge = startX <= EDGE_WIDTH;
      startFromRightEdge = startX >= window.innerWidth - EDGE_WIDTH;
    };

    const onTouchEnd = (e: TouchEvent) => {
      const t = e.changedTouches[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = Math.abs(t.clientY - startY);

      // Ignore si scroll vertical dominant
      if (dy > MAX_VERTICAL) return;

      if (startFromLeftEdge && dx > THRESHOLD && onSwipeRight) {
        onSwipeRight();
      } else if (startFromRightEdge && -dx > THRESHOLD && onSwipeLeft) {
        onSwipeLeft();
      }
    };

    document.addEventListener('touchstart', onTouchStart, { passive: true });
    document.addEventListener('touchend', onTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', onTouchStart);
      document.removeEventListener('touchend', onTouchEnd);
    };
  }, [onSwipeRight, onSwipeLeft, enabled]);
}
