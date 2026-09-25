type Name = 'flow' | 'home' | 'chart' | 'people' | 'search' | 'arrow' | 'document' | 'layers'
const paths: Record<Name, string> = {
  flow: 'M3 7c3-6 6 6 9 0s6 6 9 0M3 12c3-6 6 6 9 0s6 6 9 0M3 17c3-6 6 6 9 0s6 6 9 0',
  home: 'm3 10 9-7 9 7v10h-6v-6H9v6H3Z', chart: 'M4 20V12m8 8V4m8 16V8',
  people: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m8-7a4 4 0 0 1 0 8m5 9v-2a4 4 0 0 0-3-3.87',
  search: 'M21 21l-5-5M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16',
  arrow: 'M4 12h16m-6-6 6 6-6 6', document: 'M14 2H4v20h16V8Zm0 0v6h6M8 12h8M8 16h8',
  layers: 'm12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 17l10 5 10-5',
}
export function Icon({ name, size = 20 }: { name: Name; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
