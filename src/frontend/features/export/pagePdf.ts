import { toJpeg } from 'html-to-image'
import { PDFDocument } from 'pdf-lib'

const MARGIN = 18
const A4_SHORT_EDGE = 595.28
const A4_LONG_EDGE = 841.89

export async function buildIntelScorePagePdf(
  element: HTMLElement,
  symbol: string,
): Promise<Uint8Array> {
  await document.fonts.ready
  const bounds = element.getBoundingClientRect()
  const width = Math.ceil(bounds.width)
  const height = Math.ceil(element.scrollHeight)
  if (width < 1 || height < 1) throw new Error('IntelScore page is empty')
  const companyHeader = element.querySelector<HTMLElement>('[aria-label="Company market summary"]')
  if (!companyHeader) throw new Error('IntelScore content not found')
  const origin = bounds.top
  const contentStart = Math.max(0, companyHeader.getBoundingClientRect().top - origin)
  const breakPositions = [
    ...element.querySelectorAll<HTMLElement>('h2, h3, h4, header, section, article, footer'),
  ]
    .map((node) => node.getBoundingClientRect().top - origin)
    .filter((top) => top > contentStart)

  // Keep the current responsive layout and theme, while bounding canvas memory.
  const pixelRatio = Math.min(
    2,
    2200 / width,
    Math.sqrt(24_000_000 / (width * height)),
    32_000 / height,
  )
  const backgroundColor = getComputedStyle(document.documentElement).backgroundColor
  const capture = await toJpeg(element, {
    width,
    height,
    pixelRatio,
    quality: 0.96,
    backgroundColor,
    preferredFontFormat: 'woff2',
  })

  const image = new Image()
  image.src = capture
  await image.decode()

  const pdf = await PDFDocument.create()
  pdf.setTitle(`${symbol} IntelScore | IntelFlow`)
  pdf.setAuthor('IntelFlow')
  pdf.setSubject('Visual copy of the displayed IntelScore research page')

  const landscape = width >= 900
  const pageWidth = landscape ? A4_LONG_EDGE : A4_SHORT_EDGE
  const pageHeight = landscape ? A4_SHORT_EDGE : A4_LONG_EDGE
  const contentWidth = pageWidth - MARGIN * 2
  const contentHeight = pageHeight - MARGIN * 2
  const scale = image.naturalHeight / height
  const safeBreaks = breakPositions.map((top) => Math.round(top * scale)).sort((a, b) => a - b)
  const slicePixelHeight = Math.floor((image.naturalWidth * contentHeight) / contentWidth)
  const start = Math.round(contentStart * scale)
  const pageCount = Math.ceil((image.naturalHeight - start) / slicePixelHeight)
  for (let offset = start, pageIndex = 0; offset < image.naturalHeight; pageIndex += 1) {
    const maximumEnd = Math.min(offset + slicePixelHeight, image.naturalHeight)
    const minimumEnd = Math.max(
      offset + slicePixelHeight * 0.82,
      image.naturalHeight - (pageCount - pageIndex - 1) * slicePixelHeight,
    )
    const nearbyBreak = safeBreaks
      .filter((point) => point >= minimumEnd && point < maximumEnd)
      .at(0)
    const end = nearbyBreak ?? maximumEnd
    const sliceHeight = end - offset
    const canvas = document.createElement('canvas')
    canvas.width = image.naturalWidth
    canvas.height = sliceHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Could not prepare PDF page')
    context.drawImage(
      image,
      0,
      offset,
      image.naturalWidth,
      sliceHeight,
      0,
      0,
      image.naturalWidth,
      sliceHeight,
    )
    const pageImage = await pdf.embedJpg(canvas.toDataURL('image/jpeg', 0.96))
    const displayedHeight = (sliceHeight * contentWidth) / image.naturalWidth
    const page = pdf.addPage([pageWidth, pageHeight])
    page.drawImage(pageImage, {
      x: MARGIN,
      y: pageHeight - MARGIN - displayedHeight,
      width: contentWidth,
      height: displayedHeight,
    })
    canvas.width = 0
    canvas.height = 0
    offset = end
  }

  return pdf.save()
}
