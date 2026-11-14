import { AdminPage } from '../../../components/figma-pages/AdminPage'

export const metadata = {
  title: 'Audit Logs · The Handover',
  description: 'Immutable record of access, verification, publication and configuration changes.',
}

export default function SettingsAuditLogsRoute() {
  return <AdminPage view="audit" />
}
