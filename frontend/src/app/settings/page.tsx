import { AdminPage } from '../../components/figma-pages/AdminPage'

export const metadata = {
  title: 'Settings · The Handover',
  description: 'Workspace-wide configuration, AI, retention, privacy and permissions.',
}

export default function SettingsRoute() {
  return <AdminPage view="settings" />
}
