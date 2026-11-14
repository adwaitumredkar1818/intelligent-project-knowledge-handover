import { AuthPage } from '../../components/figma-pages/AuthPage'

export const metadata = {
  title: 'Reset Password · The Handover',
  description: 'Reset your Handover workspace password.',
}

export default function ForgotPasswordRoute() {
  return <AuthPage view="forgot-password" />
}
