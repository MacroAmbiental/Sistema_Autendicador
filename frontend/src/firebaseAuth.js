import { initializeApp, getApps } from 'firebase/app'
import {
  browserLocalPersistence,
  getAuth,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth'

const SESSION_KEY = 'autenticador.firebase.loginUntil'
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000

let authSingleton = null
let persistenceReady = null

function getFirebaseConfig() {
  return {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
  }
}

function ensureConfig(config) {
  const missing = Object.entries(config)
    .filter(([, value]) => !value)
    .map(([key]) => key)

  if (missing.length) {
    throw new Error(`Firebase nao configurado. Variaveis ausentes: ${missing.join(', ')}`)
  }
}

export function getAuthInstance() {
  if (authSingleton) return authSingleton

  const config = getFirebaseConfig()
  ensureConfig(config)

  const app = getApps()[0] || initializeApp(config)
  authSingleton = getAuth(app)
  return authSingleton
}

async function ensurePersistence() {
  if (persistenceReady) return persistenceReady
  const auth = getAuthInstance()
  persistenceReady = setPersistence(auth, browserLocalPersistence)
  return persistenceReady
}

function saveSessionDeadline() {
  const deadline = Date.now() + THIRTY_DAYS_MS
  localStorage.setItem(SESSION_KEY, String(deadline))
}

function isSessionExpired() {
  const value = localStorage.getItem(SESSION_KEY)
  if (!value) return true
  const deadline = Number(value)
  if (!Number.isFinite(deadline)) return true
  return Date.now() > deadline
}

function clearSessionDeadline() {
  localStorage.removeItem(SESSION_KEY)
}

export async function loginWithEmailPassword(email, password) {
  await ensurePersistence()
  const auth = getAuthInstance()
  const credential = await signInWithEmailAndPassword(auth, email.trim(), password)
  saveSessionDeadline()
  return credential.user
}

export async function logoutFirebase() {
  const auth = getAuthInstance()
  clearSessionDeadline()
  await signOut(auth)
}

export async function logoutToLogin() {
  try {
    await logoutFirebase()
  } finally {
    window.location.replace('/login')
  }
}

export async function getCurrentIdToken() {
  const auth = getAuthInstance()
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}

export function subscribeAuth(callback) {
  const auth = getAuthInstance()

  ensurePersistence().catch((error) => {
    callback({ type: 'error', error })
  })

  return onAuthStateChanged(auth, async (user) => {
    if (!user) {
      clearSessionDeadline()
      callback({ type: 'signed-out', user: null })
      return
    }

    if (isSessionExpired()) {
      await signOut(auth)
      clearSessionDeadline()
      callback({ type: 'expired', user: null })
      return
    }

    callback({ type: 'signed-in', user })
  })
}
