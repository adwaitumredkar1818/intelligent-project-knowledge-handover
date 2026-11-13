"use client";

import React, { useState, useEffect, useRef } from "react";

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    el.querySelectorAll(".reveal").forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);
  return ref;
}

const FAQ_ITEMS = [
  {
    q: "What does Handover do?",
    a: "Handover connects authorized organizational tools (GitHub, Jira, Slack, uploaded documents), reconstructs fragmented project context into structured findings (decisions, technical architecture, responsibilities, risks, and dependencies), enables human verification against raw evidence, and produces auditable transition packages for successors.",
  },
  {
    q: "Which tools can Handover connect to?",
    a: "Handover supports fine-grained read-only integrations with GitHub repositories, Jira projects, Slack channels, and direct uploads of PDF and DOCX documentation (such as Architecture Decision Records and operational runbooks). You choose explicitly which repositories and channels to index.",
  },
  {
    q: "Does Handover replace our existing project management tools?",
    a: "No. Handover is not a task tracker or issue management system. It reads from the tools your engineering and product teams already use and focuses on preserving architectural memory, critical context, and transition management. Daily work continues in GitHub and Jira.",
  },
  {
    q: "How does Handover use AI?",
    a: "AI models extract candidate findings from authorized evidence chunks, detect contradictions across sources, score extraction confidence, and synthesize draft summaries. The LLM is strictly not a source of truth—it cannot independently approve handovers, override source permissions, or invent project facts.",
  },
  {
    q: "Can team members verify AI-generated findings?",
    a: "Yes. Human verification is a mandatory platform gate. Outgoing members and project leads inspect findings, review citations, edit descriptions, flag conflicts, or reject invalid candidates. Only human-verified items contribute to official handover completeness scores.",
  },
  {
    q: "Who can use Handover?",
    a: "Engineering leaders, project managers, technical leads, outgoing employees, incoming successors, researchers, and student developers transitioning responsibilities. Workspaces support role-based access control with granular project-level permissions.",
  },
  {
    q: "Can users belong to multiple projects with different transition roles?",
    a: "Yes. Roles and transition participation are assigned per project. A team member can be an outgoing contributor on one project, an approving project manager on another, and an incoming successor on a third.",
  },
  {
    q: "Can existing project documentation be uploaded?",
    a: "Yes. Teams can upload PDF and DOCX documents such as architecture proposals, onboarding guides, and post-mortems. They are parsed, indexed with OCR where appropriate, and linked into the knowledge graph alongside repository and issue tracker evidence.",
  },
];

export function FaqSection() {
  const ref = useReveal<HTMLElement>();
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const toggle = (i: number) => {
    setOpenIndex(openIndex === i ? null : i);
  };

  return (
    <section ref={ref} id="faq" className="scroll-mt-20 py-24 sm:py-32">
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="grid gap-12 grid-cols-1 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          {/* Header Column */}
          <div>
            <div className="reveal">
              <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
                <span className="h-px w-6 bg-current opacity-60" />
                Frequently Asked Questions
              </p>
            </div>
            <h2 className="reveal mt-5 text-[32px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[40px] lg:text-[44px]">
              Questions about keeping knowledge in motion?
            </h2>
          </div>

          {/* Accordion Column */}
          <ul className="reveal divide-y divide-[#D9E1F0] border-y border-[#D9E1F0]">
            {FAQ_ITEMS.map((item, i) => (
              <li key={item.q}>
                <button
                  onClick={() => toggle(i)}
                  aria-expanded={openIndex === i}
                  className="flex w-full items-center justify-between gap-6 py-5 text-left cursor-pointer focus:outline-none"
                >
                  <span className="text-[17px] font-semibold tracking-[-0.01em] text-[#203653]">
                    {item.q}
                  </span>
                  <span
                    className={`flex size-8 shrink-0 items-center justify-center rounded-full border border-[#D9E1F0] transition-all duration-300 ${
                      openIndex === i
                        ? "rotate-45 border-[#203653] bg-[#203653] text-white"
                        : "text-[#718096] hover:border-[#315FBA] hover:text-[#315FBA]"
                    }`}
                  >
                    <span className="text-lg leading-none font-light">+</span>
                  </span>
                </button>
                <div
                  className={`grid transition-all duration-300 ease-out ${
                    openIndex === i
                      ? "grid-rows-[1fr] opacity-100"
                      : "grid-rows-[0fr] opacity-0"
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="max-w-2xl pb-6 text-[15px] leading-relaxed text-[#56657c]">
                      {item.a}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
