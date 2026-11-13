import { Suspense } from "react";
import { LoginPage } from "../../components/auth/LoginPage";

export const metadata = {
  title: "Sign In · The Handover",
  description: "Sign in to your Handover project knowledge workspace.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <LoginPage />
    </Suspense>
  );
}
