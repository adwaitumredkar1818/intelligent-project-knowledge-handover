'use client'

// OrganicScene.tsx — Stub for the optional 3D sphere component.
// SphereVisual in index.tsx lazy-loads this and falls back to StaticSphereFallback
// if the import fails (which it will in production until the actual 3D scene is built).

import type { SceneProps } from './index'
import { StaticSphereFallback } from './index'

export default function OrganicScene(props: SceneProps) {
  return <StaticSphereFallback className={props.className} dark={props.dark} />
}
