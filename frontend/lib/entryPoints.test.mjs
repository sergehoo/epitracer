// Point d'entrée dépendant du moyen de transport (formulaire voyageur, étape 1).
// Exécution : npm test (node --test, TypeScript chargé nativement par Node ≥ 23.6).
import assert from 'node:assert/strict';
import test from 'node:test';

import { compatibleEntryPoints, keptEntryPoint, noCompatibleEntryPointMessage } from './entryPoints.ts';

const POINTS = [
  { code: 'ABJ-AIRPORT', name: 'Aéroport FHB', type: 'airport' },
  { code: 'ABJ-PORT', name: "Port d'Abidjan", type: 'seaport' },
  { code: 'RIV', name: 'Point fluvial', type: 'river' },
  { code: 'NDA-LAND', name: 'Frontière de Niablé', type: 'land' },
];
const codes = (transport) => compatibleEntryPoints(POINTS, transport).map((p) => p.code);

test('avion → aéroports ; bateau → ports maritimes et fluviaux', () => {
  assert.deepEqual(codes('plane'), ['ABJ-AIRPORT']);
  assert.deepEqual(codes('boat'), ['ABJ-PORT', 'RIV']);
});

test('voiture, bus, à pied → postes-frontières terrestres', () => {
  for (const transport of ['car', 'bus', 'foot']) assert.deepEqual(codes(transport), ['NDA-LAND']);
});

test('train sans point ferroviaire ouvert → aucun choix et message clair', () => {
  assert.deepEqual(codes('train'), []);
  assert.match(noCompatibleEntryPointMessage('train'), /Aucun point d'entrée ferroviaire n'est actuellement ouvert/);
});

test('« Autre » → tous les points ouverts ; transport non choisi → aucun', () => {
  assert.equal(codes('other').length, POINTS.length);
  assert.deepEqual(codes(''), []);
});

test('changement de transport : le point devenu incompatible est vidé, un point compatible est gardé', () => {
  assert.equal(keptEntryPoint('ABJ-AIRPORT', compatibleEntryPoints(POINTS, 'boat')), '');
  assert.equal(keptEntryPoint('RIV', compatibleEntryPoints(POINTS, 'boat')), 'RIV');
  assert.equal(keptEntryPoint('FERME', compatibleEntryPoints(POINTS, 'plane')), '');
});
