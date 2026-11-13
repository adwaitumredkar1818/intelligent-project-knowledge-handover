import { Suspense } from "react";
import { SignupPage } from "../../components/auth/SignupPage";

export const metadata = {
  title: "Create Account · The Handover",
  description: "Create your Handover account to start capturing project knowledge.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <SignupPage />
    </Suspense>
  );
}
