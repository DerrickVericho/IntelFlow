import { useState } from 'react'
import type { Research } from '../../types/research'

export function DownloadPdfButton({ data }: { data: Research }) {
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(false)

  async function download() {
    if (working) return
    setWorking(true)
    setError(false)
    try {
      const page = document.querySelector<HTMLElement>('[data-intelscore-pdf]')
      if (!page) throw new Error('IntelScore page not found')
      const { buildIntelScorePagePdf } = await import('./pagePdf')
      const bytes = await buildIntelScorePagePdf(page, data.symbol)
      const blob = new Blob([new Uint8Array(bytes)], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `IntelFlow_${data.symbol}_IntelScore_${data.as_of ?? 'undated'}.pdf`
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch {
      setError(true)
    } finally {
      setWorking(false)
    }
  }

  return (
    <div className="flex flex-col items-stretch gap-2 sm:items-end">
      <button
        type="button"
        onClick={() => void download()}
        disabled={working}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-control bg-surface px-4 text-sm font-semibold text-ink hover:bg-raised focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-wait disabled:opacity-60"
      >
        <svg
          aria-hidden="true"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v3h16v-3" />
        </svg>
        {working ? 'Preparing PDF…' : 'Save as PDF'}
      </button>
      {error && (
        <p role="alert" className="text-sm text-negative">
          PDF could not be prepared. Please try again.
        </p>
      )}
    </div>
  )
}
