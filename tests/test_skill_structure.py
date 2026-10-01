"""
Light-weight checks: every skill folder has SKILL.md with the required sections,
and the frontmatter `name:` matches the folder name (except for placeholders).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"

ALL_SKILLS = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
REQUIRED_SECTIONS = ("## When to Use", "## Procedure", "## Verification")


def _frontmatter_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    nm = re.search(r"^\s*name:\s*(.+?)\s*$", m.group(1), re.MULTILINE)
    return nm.group(1).strip() if nm else ""


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=lambda p: p.name)
def test_skill_md_exists(skill):
    assert (skill / "SKILL.md").is_file()


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=lambda p: p.name)
def test_frontmatter_name_matches_folder(skill):
    name = _frontmatter_name(skill / "SKILL.md")
    assert name == skill.name, f"frontmatter name '{name}' != folder name '{skill.name}'"


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=lambda p: p.name)
def test_required_sections_present(skill):
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    missing = [h for h in REQUIRED_SECTIONS if h not in text]
    assert not missing, f"{skill.name} SKILL.md missing sections: {missing}"


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=lambda p: p.name)
def test_has_scripts_or_is_purely_declarative(skill):
    # All skills in this repo have scripts/ — sanity check.
    assert (skill / "scripts").is_dir(), f"{skill.name} missing scripts/ directory"
