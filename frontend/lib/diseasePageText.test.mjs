// Fiche maladie publique FR/EN : langue du cookie, libellés de la fiche, requêtes API par langue.
// Exécution : npm test (node --test, TypeScript chargé nativement par Node ≥ 23.6).
import assert from 'node:assert/strict';
import test from 'node:test';

import { DISEASE_TEXT, diseaseLocale, formatDiseaseDate } from './diseasePageText.ts';
import { fetchPublicDisease } from './portal.ts';

test('langue de la fiche : cookie du sélecteur, français par défaut', () => {
  assert.equal(diseaseLocale('en'), 'en');
  assert.equal(diseaseLocale('fr'), 'fr');
  assert.equal(diseaseLocale(undefined), 'fr');
  assert.equal(diseaseLocale('de'), 'fr');
});

test('libellés statiques traduits, mêmes clés en FR et EN', () => {
  const { fr, en } = DISEASE_TEXT;
  assert.deepEqual(Object.keys(en).sort(), Object.keys(fr).sort());
  assert.equal(en.symptoms, 'Symptoms');
  assert.equal(en.followup, 'Traveller follow-up');
  assert.equal(en.incubationDays(2, 21), '2 to 21 days');
  assert.equal(fr.incubationDays(2, 21), '2 à 21 jours');
  assert.equal(en.followupDays(21), '21 days if needed');
  assert.equal(formatDiseaseDate('2026-11-18T10:00:00Z', 'en'), '18 November 2026');
  assert.equal(formatDiseaseDate('2026-11-18T10:00:00Z', 'fr'), '18 novembre 2026');
});

test('note de repli affichée seulement en anglais', () => {
  assert.equal(DISEASE_TEXT.fr.untranslated, '');
  assert.match(DISEASE_TEXT.en.untranslated, /shown in French/);
});

test('cache : FR et EN interrogent deux URL distinctes (clés de cache séparées)', async () => {
  const urls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url) => {
    urls.push(String(url));
    return new Response(JSON.stringify({ slug: 'ebola' }), { status: 200 });
  };
  try {
    await fetchPublicDisease('ebola');
    await fetchPublicDisease('ebola', 'en');
  } finally {
    globalThis.fetch = original;
  }
  assert.equal(urls.length, 2);
  assert.match(urls[0], /\/api\/v1\/public\/diseases\/ebola\/$/);
  assert.match(urls[1], /\/api\/v1\/public\/diseases\/ebola\/\?lang=en$/);
});
