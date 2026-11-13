import { Suspense } from "react";
import { ForgotPasswordPage } from "../../components/auth/ForgotPasswordPage";

export const metadata = {
  title: "Reset Password · The Handover",
  description: "Reset your Handover workspace password.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <ForgotPasswordPage />
    </Suspense>
  );
}
