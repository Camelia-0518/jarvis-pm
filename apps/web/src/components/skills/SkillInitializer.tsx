"use client";

import { useEffect } from "react";
import { loadSkillDefinitionsFromBackend } from "@/services/skills/registry";

export function SkillInitializer() {
  useEffect(() => {
    loadSkillDefinitionsFromBackend();
  }, []);

  return null;
}
