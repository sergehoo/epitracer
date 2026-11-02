// Non-régression : boucle « Changement de mot de passe obligatoire ».
// Exécution : npm test (node --test, TypeScript chargé nativement par Node ≥ 23.6).
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  FORCED_CHANGE_PATH,
  HOME_PATH,
  LOGIN_PATH,
  dashboardRedirect,
  forcedChangeRedirect,
  routeAfterLogin,
  routeAfterPasswordChange,
} from './authFlow.ts';

const PENDING = { must_change_password: true };
const DONE = { must_change_password: false };

test('première connexion avec mot de passe temporaire → changement imposé', () => {
  assert.equal(routeAfterLogin(PENDING), FORCED_CHANGE_PATH);
});

test('changement réussi avec session renouvelée → dashboard, sans nouveau login', () => {
  assert.equal(
    routeAfterPasswordChange({ access: 'a', refresh: 'r', must_change_password: false }),
    HOME_PATH,
  );
});

test('changement sans nouveaux jetons (ancien serveur) → reconnexion, pas de boucle', () => {
  assert.equal(routeAfterPasswordChange({}), LOGIN_PATH);
  assert.equal(routeAfterLogin(DONE), HOME_PATH);
});

test('reconnexion avec le nouveau mot de passe → dashboard', () => {
  assert.equal(routeAfterLogin(DONE), HOME_PATH);
  assert.equal(dashboardRedirect(DONE), null);
});

test('obligation en cours : le dashboard renvoie vers le changement, qui reste affiché', () => {
  assert.equal(dashboardRedirect(PENDING), FORCED_CHANGE_PATH);
  assert.equal(forcedChangeRedirect(PENDING), null);
});

test('rafraîchissement de page : aucun aller-retour dashboard ↔ changement', () => {
  for (const state of [PENDING, DONE, {}]) {
    const fromDashboard = dashboardRedirect(state);
    const fromForcedPage = forcedChangeRedirect(state);
    // Au plus une des deux pages redirige, et jamais vers l'autre qui redirigerait à son tour.
    assert.ok(!(fromDashboard && fromForcedPage), `boucle pour ${JSON.stringify(state)}`);
    // Une seconde évaluation (F5) donne la même décision : état stable.
    assert.equal(dashboardRedirect(state), fromDashboard);
    assert.equal(forcedChangeRedirect(state), fromForcedPage);
  }
});

test('obligation déjà levée : la page de changement imposé renvoie au dashboard', () => {
  assert.equal(forcedChangeRedirect(DONE), HOME_PATH);
});
