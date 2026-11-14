"use client";

import { Agentation } from "agentation";
import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

export function AgentationToolbar() {
  const isClient = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );

  if (!isClient || process.env.NEXT_PUBLIC_ENABLE_AGENTATION !== "true") {
    return null;
  }

  return <Agentation endpoint="http://localhost:4747" />;
}
