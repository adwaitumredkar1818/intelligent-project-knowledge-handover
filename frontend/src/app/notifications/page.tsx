import { AdminPage } from '../../components/figma-pages/AdminPage'

export const metadata = {
  title: 'Notifications · The Handover',
  description: 'Review requests, approvals, ingestion updates and integration alerts.',
}

export default function NotificationsRoute() {
  return <AdminPage view="notifications" />
}
