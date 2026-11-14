import { AdminPage } from '../../../components/figma-pages/AdminPage'

export const metadata = {
  title: 'Profile & Account · The Handover',
  description: 'Your personal information, security and preferences.',
}

export default function SettingsProfileRoute() {
  return <AdminPage view="profile" />
}
