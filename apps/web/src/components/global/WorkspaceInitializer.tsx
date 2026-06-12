"use client";

import { useEffect } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";

/** Initializes workspace store on app mount */
export function WorkspaceInitializer() {
  const fetchWorkspaces = useWorkspaceStore((s) => s.fetchWorkspaces);

  useEffect(() => {
    fetchWorkspaces();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}
