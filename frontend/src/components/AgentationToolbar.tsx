"use client";

import { Agentation } from "agentation";
import { useEffect, useState } from "react";

export function AgentationToolbar() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Only mount if explicitly enabled via environment variable
    if (process.env.NEXT_PUBLIC_ENABLE_AGENTATION === "true") {
      setMounted(true);
    }
  }, []);

  if (!mounted) {
    return null;
  }

  return <Agentation endpoint="http://localhost:4747" />;
}
