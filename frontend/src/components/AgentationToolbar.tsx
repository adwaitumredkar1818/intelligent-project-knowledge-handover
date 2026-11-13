"use client";

import { Agentation } from "agentation";
import { useEffect, useState } from "react";

export function AgentationToolbar() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return <Agentation endpoint="http://localhost:4747" />;
}
