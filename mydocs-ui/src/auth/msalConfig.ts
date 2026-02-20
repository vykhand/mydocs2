import { type Configuration, LogLevel } from '@azure/msal-browser'

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_ENTRA_CLIENT_ID || '',
    authority: import.meta.env.VITE_ENTRA_AUTHORITY || 'https://login.microsoftonline.com/common',
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
      loggerCallback: (_level, message) => {
        console.debug('[MSAL]', message)
      },
    },
  },
}

export const loginRequest = {
  scopes: [
    `api://${import.meta.env.VITE_ENTRA_CLIENT_ID || ''}/access_as_user`,
  ],
}
