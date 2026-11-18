// Combobox pays (provenance, transit, séjour récent) : recherche sur le référentiel local.
// Exécution : npm test (node --test, TypeScript chargé nativement par Node ≥ 23.6).
import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCountryOptions, findExactCountry, searchCountries } from './countrySearch.ts';
import { COUNTRIES } from './datasets.ts';

const FR = buildCountryOptions(COUNTRIES, 'fr');
const EN = buildCountryOptions(COUNTRIES, 'en');
const codes = (query, options = FR) => searchCountries(options, query).map((o) => o.code);

test('tous les pays du référentiel sont proposés, pas seulement les pays à risque', () => {
  const offered = codes('');
  assert.equal(offered.length, COUNTRIES.length - 1); // AN : code ISO retiré, jamais proposé
  for (const code of ['FR', 'JP', 'BR', 'NZ', 'IS', 'CI', 'CD']) assert.ok(offered.includes(code), code);
  assert.ok(!offered.includes('AN'));
  assert.equal(offered[0], 'AF'); // ordre alphabétique : Afghanistan en tête
});

test('recherche dès le premier caractère, insensible aux accents, à la casse et à la ponctuation', () => {
  assert.ok(codes('z').slice(0, 2).every((c) => ['ZM', 'ZW'].includes(c)));
  assert.equal(codes('cote d ivoire')[0], 'CI');
  assert.equal(codes("CÔTE D'IVOIRE")[0], 'CI');
  assert.equal(codes('egypte')[0], 'EG');
  assert.equal(codes('senegal')[0], 'SN');
});

test('noms anglais, code ISO et appellations usuelles', () => {
  assert.equal(codes('germany')[0], 'DE');
  assert.equal(codes('ivory')[0], 'CI');
  assert.equal(codes('ci')[0], 'CI');
  assert.equal(codes('rdc')[0], 'CD');
  assert.equal(codes('usa')[0], 'US');
});

test('aucun pays hors référentiel : saisie libre sans correspondance', () => {
  assert.deepEqual(codes('Wakanda'), []);
  assert.equal(findExactCountry(FR, 'Wakanda'), undefined);
  assert.equal(findExactCountry(FR, 'fran'), undefined); // début de nom : il faut choisir dans la liste
  assert.equal(findExactCountry(FR, 'france')?.code, 'FR');
  assert.equal(findExactCountry(FR, 'Germany')?.code, 'DE');
});

test('libellés français par défaut, anglais en EN ; le code ISO alpha-2 reste la valeur', () => {
  const de = (options) => options.find((o) => o.code === 'DE');
  assert.equal(de(FR).label, 'Allemagne');
  assert.equal(de(EN).label, 'Germany');
  assert.equal(codes('allemagne', EN)[0], 'DE'); // le nom français reste cherchable en EN
});
