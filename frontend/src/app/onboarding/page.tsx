import { Suspense } from "react";
import { OnboardingPage } from "../../components/auth/OnboardingPage";

export const metadata = {
  title: "Get Started · Handover Onboarding",
  description: "Set up your profile, workspace, and experience Handover knowledge reconstruction.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F6F8FC]" />}>
      <OnboardingPage />
    </Suspense>
  );
}
