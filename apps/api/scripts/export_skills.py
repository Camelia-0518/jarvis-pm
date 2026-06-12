"""Export built-in skills from skill_processor_enhanced.py to JSON"""

import json
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.skill_processor_enhanced import SkillProcessorEnhanced


def main():
    processor = SkillProcessorEnhanced(enable_cache=False)
    skills = processor._skills

    data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data", "skills")
    os.makedirs(data_dir, exist_ok=True)

    output_path = os.path.join(data_dir, "builtin.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(skills)} skills to {output_path}")
    for sid in skills:
        print(f"  - {sid}")


if __name__ == "__main__":
    main()
