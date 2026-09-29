import { useSyncExternalStore } from 'react'

export type ThemePreference = 'light' | 'dark' | 'system'
const storageKey = 'intelflow-theme'
const listeners = new Set<() => void>()
let disconnect: (() => void) | undefined
const validPreference = (value: string | null | undefined): ThemePreference =>
  value === 'light' || value === 'dark' ? value : 'system'
const preference = () => validPreference(document.documentElement.dataset.themePreference)
const resolve = (value: ThemePreference) =>
  value === 'system'
    ? window.matchMedia?.('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
    : value

function apply(value: ThemePreference) {
  const root = document.documentElement
  root.dataset.themePreference = value
  root.dataset.theme = resolve(value)
  root.style.colorScheme = root.dataset.theme === 'light' ? 'only light' : 'dark'
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', root.dataset.theme === 'dark' ? '#0b192b' : '#edf3fa')
  listeners.forEach((listener) => listener())
}

export function setThemePreference(value: ThemePreference) {
  try {
    localStorage.setItem(storageKey, value)
  } catch {
    /* The choice still works when storage is blocked. */
  }
  apply(value)
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  if (listeners.size === 1) {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    const onSystemChange = () => {
      if (preference() === 'system') apply('system')
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) apply(validPreference(event.newValue))
    }
    media?.addEventListener('change', onSystemChange)
    window.addEventListener('storage', onStorage)
    disconnect = () => {
      media?.removeEventListener('change', onSystemChange)
      window.removeEventListener('storage', onStorage)
    }
  }
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      disconnect?.()
      disconnect = undefined
    }
  }
}

const snapshot = () => `${preference()}:${resolve(preference())}`
export function useTheme() {
  const value = useSyncExternalStore(subscribe, snapshot)
  const [selected, theme] = value.split(':')
  return { preference: selected as ThemePreference, theme: theme as 'light' | 'dark' }
}
