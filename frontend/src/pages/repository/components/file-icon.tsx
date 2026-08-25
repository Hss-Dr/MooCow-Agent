import IconDoc from '@/assets/repository/file/doc.svg'
import IconPdf from '@/assets/repository/file/pdf.svg'
import IconOther from '@/assets/repository/file/other.svg'
const map = {
  doc: IconDoc,
  pdf: IconPdf,
  other: IconOther,
}

export type FileIcon = keyof typeof map

export function FileIcon(props: {
  suffix: FileIcon
  className?: string
}) {
  const { suffix, className } = props
  return (
    <img src={map[suffix] || map.other} alt={suffix} className={className} />
  )
}
