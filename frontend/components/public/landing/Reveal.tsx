'use client';

import { motion } from 'framer-motion';

/** Apparition douce au défilement (désactivée si « réduire les animations »). */
export function Reveal({
  children, delay = 0, className, as = 'div',
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  as?: 'div' | 'li' | 'article';
}) {
  const Tag = motion[as];
  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.45, ease: 'easeOut', delay }}
    >
      {children}
    </Tag>
  );
}
