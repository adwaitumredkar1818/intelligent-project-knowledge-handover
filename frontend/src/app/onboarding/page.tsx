import { AuthPage } from '../../components/figma-pages/AuthPage'

export const metadata = {
  title: 'Get Started · Handover Onboarding',
  description: 'Set up your profile, workspace, and experience Handover knowledge reconstruction.',
}

export default function OnboardingRoute() {
  return <AuthPage view="onboarding" />
}
