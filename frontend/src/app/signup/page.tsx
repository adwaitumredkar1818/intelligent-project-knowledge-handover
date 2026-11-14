import { AuthPage } from '../../components/figma-pages/AuthPage'

export const metadata = {
  title: 'Create Account · The Handover',
  description: 'Create your Handover account to start capturing project knowledge.',
}

export default function SignupRoute() {
  return <AuthPage view="signup" />
}
