"use client";

import React, { useEffect } from "react";
import { BrandIntro } from "./BrandIntro";
import { LandingNav } from "./LandingNav";
import { HeroSection } from "./HeroSection";
import { SectionDivider } from "./SectionDivider";
import { ProblemSection } from "./ProblemSection";
import { IntroducingSection } from "./IntroducingSection";
import { HowItWorksSection } from "./HowItWorksSection";
import { IntelligenceSection } from "./IntelligenceSection";
import { ExplorerSection } from "./ExplorerSection";
import { HandoversSection } from "./HandoversSection";
import { RolesSection } from "./RolesSection";
import { TrustSection } from "./TrustSection";
import { FaqSection } from "./FaqSection";
import { FinalCtaSection } from "./FinalCtaSection";
import { LandingFooter } from "./LandingFooter";

export function LandingPage() {
  useEffect(() => {
    // Reset scroll to top on initial page mount if no hash is present
    if (!window.location.hash) {
      window.scrollTo(0, 0);
    }
  }, []);

  return (
    <div className="ambient-canvas min-h-screen w-full max-w-full overflow-x-hidden text-[#203653] font-sans antialiased selection:bg-[#315FBA]/15 selection:text-[#203653]">
      {/* Branded Opening Transition Experience */}
      <BrandIntro />

      {/* 1. Navigation */}
      <LandingNav />

      <main>
        {/* 2. Hero with Organic Knowledge Sphere */}
        <HeroSection />

        {/* Section Divider: Hero -> Problem (Animated travelling light beam) */}
        <SectionDivider label="SEC_01 // THE_PROBLEM" />

        {/* 3. Problem */}
        <ProblemSection />

        <SectionDivider label="SEC_02 // KNOWLEDGE_SYNTHESIS" />

        {/* 4. Introducing Handover */}
        <IntroducingSection />

        <SectionDivider label="SEC_03 // VERIFICATION_LIFECYCLE" />

        {/* 5. How It Works */}
        <HowItWorksSection />

        <SectionDivider label="SEC_04 // INTELLIGENCE_DOMAINS" />

        {/* 6. Knowledge Intelligence */}
        <IntelligenceSection />

        <SectionDivider label="SEC_05 // RELATIONSHIP_GRAPH" />

        {/* 7. Knowledge Explorer */}
        <ExplorerSection />

        <SectionDivider label="SEC_06 // AUDITABLE_TRANSFERS" />

        {/* 8. Structured Handovers */}
        <HandoversSection />

        <SectionDivider label="SEC_07 // ROLE_EXPERIENCES" />

        {/* 9. Role-Based Experiences */}
        <RolesSection />

        <SectionDivider label="SEC_08 // TRUST_AND_SECURITY" />

        {/* 10. Trust & Security */}
        <TrustSection />

        <SectionDivider label="SEC_09 // FREQUENTLY_ASKED" />

        {/* 11. FAQ */}
        <FaqSection />

        {/* 12. Final CTA */}
        <FinalCtaSection />
      </main>

      {/* 13. Footer */}
      <LandingFooter />
    </div>
  );
}

export default LandingPage;
