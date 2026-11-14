import { AdminPage } from '../../../components/figma-pages/AdminPage'

export const metadata = {
  title: 'Team Management · The Handover',
  description: 'Workspace members and roles management.',
}

export default function SettingsTeamRoute() {
  return <AdminPage view="team" />
}
