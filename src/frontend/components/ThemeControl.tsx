import { setThemePreference, useTheme, type ThemePreference } from '../app/theme'

export function ThemeControl() {
  const { preference } = useTheme()
  return <label className="flex items-center gap-2 text-sm text-muted"><span className="hidden sm:inline">Appearance</span>
    <select className="min-h-10 rounded-xl border border-control bg-surface px-3 py-2 text-sm text-ink" aria-label="Color theme" value={preference} onChange={event => setThemePreference(event.target.value as ThemePreference)}>
      <option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option>
    </select>
  </label>
}
