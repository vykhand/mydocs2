import { ref, computed } from 'vue'
import {
  PublicClientApplication,
  InteractionRequiredAuthError,
  type AccountInfo,
  type SilentRequest,
} from '@azure/msal-browser'
import { msalConfig, loginRequest } from './msalConfig'

const msalInstance = new PublicClientApplication(msalConfig)
const isInitialized = ref(false)
const account = ref<AccountInfo | null>(null)

export function useAuth() {
  const isAuthenticated = computed(() => !!account.value)
  const userName = computed(() => account.value?.name || account.value?.username || '')

  async function initialize() {
    if (isInitialized.value) return
    await msalInstance.initialize()
    const response = await msalInstance.handleRedirectPromise()
    if (response?.account) {
      account.value = response.account
      msalInstance.setActiveAccount(response.account)
    } else {
      const accounts = msalInstance.getAllAccounts()
      if (accounts.length > 0) {
        account.value = accounts[0]
        msalInstance.setActiveAccount(accounts[0])
      }
    }
    isInitialized.value = true
  }

  async function login() {
    await msalInstance.loginRedirect(loginRequest)
  }

  async function logout() {
    await msalInstance.logoutRedirect({
      postLogoutRedirectUri: window.location.origin,
    })
  }

  async function getAccessToken(): Promise<string> {
    if (!account.value) throw new Error('Not authenticated')
    const silentRequest: SilentRequest = {
      ...loginRequest,
      account: account.value,
    }
    try {
      const response = await msalInstance.acquireTokenSilent(silentRequest)
      return response.accessToken
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) {
        await msalInstance.acquireTokenRedirect(loginRequest)
        // The redirect will reload the page; this line won't execute.
        return ''
      }
      throw error
    }
  }

  return {
    isInitialized,
    isAuthenticated,
    account,
    userName,
    initialize,
    login,
    logout,
    getAccessToken,
  }
}
