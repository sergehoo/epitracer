'use client';

import Image, { type StaticImageData } from 'next/image';
import { useState } from 'react';

/**
 * Photographie locale optimisée (Next/Image + flou de chargement) avec repli :
 * si le fichier ne peut pas être servi, un dégradé aux couleurs nationales
 * remplace l'image — jamais d'icône d'image cassée ni de rectangle vide.
 */
export function LandingPhoto({
  src,
  alt,
  sizes,
  priority = false,
  className = '',
}: {
  src: StaticImageData;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        role="img"
        aria-label={alt}
        className={`absolute inset-0 bg-gradient-to-br from-ciForest via-emerald-700 to-ciOrange/80 ${className}`}
      />
    );
  }
  return (
    <Image
      src={src}
      alt={alt}
      fill
      sizes={sizes}
      priority={priority}
      placeholder="blur"
      onError={() => setFailed(true)}
      className={`object-cover ${className}`}
    />
  );
}
