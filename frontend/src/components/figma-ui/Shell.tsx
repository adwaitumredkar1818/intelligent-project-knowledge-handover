'use client'

// Shell.tsx — Minimal stub exported for use by domain.tsx and pages.
// The full shell implementation is in the production layout.

import type { ProjectRole, MemberRole } from '../../lib/figmaStore'
import { ROLE_LABEL } from '../../lib/figmaStore'
import { Badge } from './index'

export const ROLE_TONE: Record<ProjectRole, 'blue' | 'amber' | 'green'> = {
  manager: 'blue',
  outgoing: 'amber',
  incoming: 'green',
}

export function RoleBadge({ role, className }: { role: MemberRole | ProjectRole; className?: string }) {
  const tone = ROLE_TONE[role as ProjectRole] || 'blue'
  const label = ROLE_LABEL[role as MemberRole] || role
  return <Badge tone={tone} dot className={className}>{label}</Badge>
}
