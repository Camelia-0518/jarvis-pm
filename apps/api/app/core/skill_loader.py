"""Skill configuration loader - supports external JSON + built-in fallback"""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "skills")
BUILTIN_FILE = os.path.join(SKILLS_DIR, "builtin.json")


def load_skills_from_json(directory: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load skill definitions from JSON files in directory.

    Priority:
    1. Individual .json files in the directory (allows overriding builtin)
    2. builtin.json (exported from code)
    3. Empty dict if nothing found
    """
    skills: Dict[str, Dict[str, Any]] = {}
    directory = directory or SKILLS_DIR

    if not os.path.isdir(directory):
        logger.warning("Skills directory not found: %s", directory)
        return skills

    # Load builtin first (as fallback base)
    if os.path.isfile(BUILTIN_FILE):
        try:
            with open(BUILTIN_FILE, "r", encoding="utf-8") as f:
                builtin = json.load(f)
                if isinstance(builtin, dict):
                    skills.update(builtin)
                    logger.info("Loaded %d builtin skills from %s", len(builtin), BUILTIN_FILE)
        except Exception as e:
            logger.warning("Failed to load builtin skills: %s", e)

    # Override with individual skill files
    overridden = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json") or filename == "builtin.json":
            continue
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                skill = json.load(f)
                if isinstance(skill, dict) and "id" in skill:
                    sid = skill["id"]
                    skills[sid] = skill
                    overridden += 1
                elif isinstance(skill, dict):
                    # File contains multiple skills
                    for sid, s in skill.items():
                        if isinstance(s, dict):
                            skills[sid] = s
                            overridden += 1
        except Exception as e:
            logger.warning("Failed to load skill file %s: %s", filepath, e)

    if overridden:
        logger.info("Overrode %d skills from individual JSON files", overridden)

    return skills


def save_skill_to_json(skill: Dict[str, Any], directory: Optional[str] = None) -> str:
    """Save a single skill definition to JSON file for hot-reload support.

    Returns:
        Path to saved file
    """
    directory = directory or SKILLS_DIR
    os.makedirs(directory, exist_ok=True)

    sid = skill.get("id", "unknown")
    filepath = os.path.join(directory, f"{sid}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(skill, f, ensure_ascii=False, indent=2)

    logger.info("Saved skill %s to %s", sid, filepath)
    return filepath
