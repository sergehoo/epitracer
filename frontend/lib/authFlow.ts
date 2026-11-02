/**
 * Décisions de navigation du parcours d'authentification console.
 *
 * Source de vérité unique : `must_change_password` tel que renvoyé par le
 * serveur (login, /auth/me/, changement de mot de passe), jamais un état
 * mémorisé côté client. Le dashboard et la page de changement imposé lisent le
 * même état : l'un ne peut pas renvoyer vers l'autre et réciproquement (pas de
 * boucle). Module sans dépendance, testé par `npm test`.
 */

export const LOGIN_PATH = '/auth/login';
export const HOME_PATH = '/dashboard';
export const FORCED_CHANGE_PATH = '/auth/change-password?forced=1';

export interface AccountState {
  must_change_password?: boolean;
}

/** Après une connexion réussie (MFA comprise). */
export function routeAfterLogin(state: AccountState): string {
  return state.must_change_password ? FORCED_CHANGE_PATH : HOME_PATH;
}

/** Garde du dashboard : redirection à faire, ou null pour afficher la page. */
export function dashboardRedirect(state: AccountState): string | null {
  return state.must_change_password ? FORCED_CHANGE_PATH : null;
}

/** Page de changement imposé : si l'obligation est déjà levée, retour au dashboard. */
export function forcedChangeRedirect(state: AccountState): string | null {
  return state.must_change_password ? null : HOME_PATH;
}

export interface PasswordChangeResponse {
  access?: string;
  refresh?: string;
  must_change_password?: boolean;
}

/**
 * Après un changement réussi : session renouvelée par le serveur → dashboard ;
 * sans nouveaux jetons → nouvelle connexion (avec le nouveau mot de passe).
 */
export function routeAfterPasswordChange(resp: PasswordChangeResponse): string {
  if (resp.access && resp.refresh && resp.must_change_password === false) return HOME_PATH;
  return LOGIN_PATH;
}
