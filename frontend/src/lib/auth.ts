import Keycloak from 'keycloak-js'
import axios from 'axios'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8081',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'hawkeye',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'hawkeye-frontend',
})

let _initialized = false

export async function initAuth(): Promise<boolean> {
  if (_initialized) return keycloak.authenticated ?? false
  try {
    const authenticated = await keycloak.init({
      onLoad: 'login-required',
      checkLoginIframe: false,
      pkceMethod: 'S256',
    })
    _initialized = true

    // Attach JWT to all axios requests
    axios.interceptors.request.use(async (config) => {
      if (keycloak.isTokenExpired(30)) {
        await keycloak.updateToken(30)
      }
      config.headers.Authorization = `Bearer ${keycloak.token}`
      return config
    })

    return authenticated
  } catch (e) {
    console.error('Keycloak init failed', e)
    return false
  }
}

export function getToken(): string | undefined {
  return keycloak.token
}

export function logout(): void {
  keycloak.logout()
}

export function getUsername(): string {
  return keycloak.tokenParsed?.preferred_username || keycloak.tokenParsed?.email || 'User'
}

export function getRoles(): string[] {
  return keycloak.tokenParsed?.realm_access?.roles || []
}

export default keycloak
