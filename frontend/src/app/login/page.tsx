import { AuthPage } from '../../components/figma-pages/AuthPage'

export const metadata = {
  title: 'Sign In · The Handover',
  description: 'Sign in to your Handover project knowledge workspace.',
}

export default function LoginRoute() {
  return <AuthPage view="login" />
}
