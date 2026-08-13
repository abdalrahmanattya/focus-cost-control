import { PublicClientApplication, type AccountInfo } from '@azure/msal-browser';

declare global {
  interface Window { __FOCUS_CONFIG__?: { apiBase?: string; authMode?: string; entraClientId?: string; entraTenantId?: string; entraApiScope?: string }; }
}

const config = window.__FOCUS_CONFIG__ ?? {};
const authMode = config.authMode || import.meta.env.VITE_AUTH_MODE || 'local';
const clientId = config.entraClientId || import.meta.env.VITE_ENTRA_CLIENT_ID || '';
const tenantId = config.entraTenantId || import.meta.env.VITE_ENTRA_TENANT_ID || '';
const apiScope = config.entraApiScope || import.meta.env.VITE_ENTRA_API_SCOPE || (clientId ? `api://${clientId}/user_impersonation` : '');
const instance = authMode === 'cloud' && clientId && tenantId ? new PublicClientApplication({
  auth: { clientId, authority: `https://login.microsoftonline.com/${tenantId}`, redirectUri: window.location.origin },
  cache: { cacheLocation: 'sessionStorage' },
}) : null;
let account: AccountInfo | null = null;

export const cloudAuth = authMode === 'cloud';
export async function initializeAuth(): Promise<void> {
  if (!instance) return;
  await instance.initialize();
  const existing = instance.getAllAccounts()[0];
  if (existing) account = existing;
}
export async function signIn(): Promise<void> {
  if (!instance) return;
  const result = await instance.loginPopup({ scopes: [apiScope] });
  account = result.account;
}
export function signedIn(): boolean { return Boolean(account); }
export function displayName(): string { return account?.name || account?.username || ''; }
export async function accessToken(): Promise<string | null> {
  if (!instance || !account) return null;
  try {
    const result = await instance.acquireTokenSilent({ account, scopes: [apiScope] });
    return result.accessToken;
  } catch {
    const result = await instance.acquireTokenPopup({ scopes: [apiScope] });
    return result.accessToken;
  }
}
