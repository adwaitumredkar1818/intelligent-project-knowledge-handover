'use client'

import { cn } from './index'
import type { SourceType, EvidenceType } from '../../lib/figmaStore'
import { FileText, GitCommitHorizontal, GitPullRequest, MessageSquare, SquareKanban, File } from 'lucide-react'

/** Official Handover mark supplied by the product owner. */
export function LogoMark({ size = 32, className, mono }: { size?: number; className?: string; mono?: boolean }) {
  return (
    <img
      src="/handover-mark.png"
      width={Math.round(size * 1.66)}
      height={size}
      className={cn('inline-block shrink-0 object-contain', mono && 'brightness-0 invert', className)}
      style={{ width: size * 1.66, height: size }}
      alt=""
      aria-hidden
    />
  )
}
export function Logo({ size = 28, className, wordmark = true, light }: { size?: number; className?: string; wordmark?: boolean; light?: boolean }) {
  return (
    <span className={cn('inline-flex items-center', className)}>
      <img
        src={wordmark ? '/handover-logo.png' : '/handover-mark.png'}
        height={size}
        className={cn('block max-w-none object-contain', light && 'brightness-0 invert')}
        style={{ height: size, width: 'auto' }}
        alt={wordmark ? 'Handover' : ''}
        aria-hidden={!wordmark || undefined}
      />
    </span>
  )
}

export function SourceIcon({ type, size = 36, className }: { type: SourceType; size?: number; className?: string }) {
  const s = size * 0.55
  const box = (bg: string, child: React.ReactNode) => (
    <span className={cn("inline-flex shrink-0 items-center justify-center rounded-[10px] border border-line", className)} style={{ width: size, height: size, background: bg }}>{child}</span>
  )
  switch (type) {
    case 'github':
      return box('#fff', <svg width={s} height={s} viewBox="0 0 24 24" fill="#203653"><path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.41-2.69 5.38-5.26 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" /></svg>)
    case 'jira':
      return box('#fff', <svg width={s} height={s} viewBox="0 0 24 24"><path d="M22.2 11.3 12.7 1.8 12 1 4.8 8.2 1.8 11.3a1 1 0 0 0 0 1.4l6.5 6.5L12 23l7.2-7.2.1-.1 2.9-2.9a1 1 0 0 0 0-1.5ZM12 15.2 8.8 12 12 8.8l3.2 3.2L12 15.2Z" fill="#2684FF" /></svg>)
    case 'slack':
      return box('#fff', <svg width={s} height={s} viewBox="0 0 24 24"><path d="M5 15a2 2 0 1 1-2-2h2v2Zm1 0a2 2 0 1 1 4 0v5a2 2 0 1 1-4 0v-5Z" fill="#E01E5A" /><path d="M9 5a2 2 0 1 1 2-2v2H9Zm0 1a2 2 0 1 1 0 4H4a2 2 0 1 1 0-4h5Z" fill="#36C5F0" /><path d="M19 9a2 2 0 1 1 2 2h-2V9Zm-1 0a2 2 0 1 1-4 0V4a2 2 0 1 1 4 0v5Z" fill="#2EB67D" /><path d="M15 19a2 2 0 1 1-2 2v-2h2Zm0-1a2 2 0 1 1 0-4h5a2 2 0 1 1 0 4h-5Z" fill="#ECB22E" /></svg>)
    case 'docs':
      return box('#EDF2FA', <FileText style={{ width: s, height: s }} className="text-brand" />)
    case 'confluence':
      return box('#fff', <svg width={s} height={s} viewBox="0 0 24 24"><path d="M2.5 17.5c-.3.5-.6 1-.8 1.4a.8.8 0 0 0 .3 1.1l4.3 2.6a.8.8 0 0 0 1.1-.3c.2-.4.5-.9.8-1.4 2-3.4 4.1-3 7.8-1.2l4.3 2a.8.8 0 0 0 1.1-.4l2-4.6a.8.8 0 0 0-.4-1c-.9-.4-2.7-1.3-4.3-2C11.8 10.8 6.5 11 2.5 17.5Z" fill="#2684FF" /><path d="M21.5 6.5c.3-.5.6-1 .8-1.4A.8.8 0 0 0 22 4L17.7 1.4a.8.8 0 0 0-1.1.3l-.8 1.4c-2 3.4-4.1 3-7.8 1.2l-4.3-2a.8.8 0 0 0-1.1.4L.6 7.3a.8.8 0 0 0 .4 1c.9.4 2.7 1.3 4.3 2 6.9 3.3 12.2 3.1 16.2-3.8Z" fill="#0052CC" /></svg>)
    case 'gdrive':
      return box('#fff', <svg width={s} height={s} viewBox="0 0 24 24"><path d="M8 3h8l7 12h-8Z" fill="#FFC107" /><path d="M1 15 8 3l4 7-7 12Z" fill="#1E88E5" opacity=".9" /><path d="M5 22h14l4-7H9Z" fill="#43A047" /></svg>)
  }
}

export function EvidenceTypeIcon({ type, className }: { type: EvidenceType; className?: string }) {
  const map = { commit: GitCommitHorizontal, pr: GitPullRequest, issue: SquareKanban, message: MessageSquare, pdf: FileText, docx: File }
  const color = { commit: 'text-slate-600 bg-slate-100', pr: 'text-violet-600 bg-violet-50', issue: 'text-blue-600 bg-blue-50', message: 'text-pink-600 bg-pink-50', pdf: 'text-red-600 bg-red-50', docx: 'text-sky-700 bg-sky-50' }[type]
  const I = map[type]
  return <span className={cn('inline-flex size-8 shrink-0 items-center justify-center rounded-lg', color, className)}><I className="size-4" /></span>
}
export const EVIDENCE_TYPE_LABEL: Record<EvidenceType, string> = { commit: 'Commit', pr: 'Pull request', issue: 'Jira issue', message: 'Slack thread', pdf: 'PDF', docx: 'DOCX' }
