"""Machine-checkable guardrails for skill paths and file-based contracts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SKILLS = (
    "text2sql-YunzhenYang-collection",
    "code-author-YunzhenYang-collection",
    "bug-hunter-YunzhenYang-collection",
    "open-sql-result-diff-YunzhenYang-collection",
)


def _skill_md(skill_name: str) -> Path:
    return REPO_ROOT / "skills" / skill_name / "SKILL.md"


def _extract_python_script_refs(text: str) -> list[str]:
    return re.findall(r"\bpython\s+(skills/[^\s'\"\n]+?\.py)\b", text)


def test_official_skill_commands_use_repo_relative_script_paths():
    for skill_name in OFFICIAL_SKILLS:
        text = _skill_md(skill_name).read_text(encoding="utf-8")
        assert "python scripts/" not in text, f"{skill_name} uses skill-relative python scripts/ path"

        refs = _extract_python_script_refs(text)
        assert refs, f"{skill_name} should document at least one repo-relative python script command"
        for ref in refs:
            path = REPO_ROOT / Path(ref)
            assert path.is_file(), f"{skill_name} references missing script: {ref}"


def test_text2sql_validation_accepts_both_schema_keys():
    script = REPO_ROOT / "skills" / "text2sql-YunzhenYang-collection" / "scripts" / "validate_sql.py"
    schema = "CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT);"

    for schema_key in ("schema_ddl", "db_schema"):
        payload = {schema_key: schema, "sql": "SELECT name FROM Students;"}
        proc = subprocess.run(
            [sys.executable, str(script), json.dumps(payload)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert '"ok": true' in proc.stdout


def test_official_run_scripts_write_to_aiase_result_path():
    cases = {
        "text2sql-YunzhenYang-collection": {
            "task_id": "contract_text2sql",
            "sql": "SELECT 1",
            "rationale": "contract smoke test",
            "confidence": 0.9,
        },
        "code-author-YunzhenYang-collection": {
            "task_id": "contract_code_author",
            "code": "def add(a, b):\n    return a + b\n",
            "loc": 2,
            "self_test_results": {"passed": 1, "failed": 0},
            "rationale": "contract smoke test",
            "confidence": 0.8,
        },
        "bug-hunter-YunzhenYang-collection": {
            "task_id": "contract_bug_hunter",
            "verdict": "clean",
            "bugs": [{"line_start": 1, "line_end": 1, "severity": "high", "type": "logic_error"}],
            "confidence": 0.7,
        },
        "open-sql-result-diff-YunzhenYang-collection": {
            "task_id": "contract_open_diff",
            "db_schema": "CREATE TABLE t (id INT);",
            "db_seed": "INSERT INTO t VALUES (1);",
            "sql_a": "SELECT id FROM t",
            "sql_b": "SELECT id FROM t",
        },
    }

    out_dir = REPO_ROOT / "dev_run_results" / "test_contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    for skill_name, payload in cases.items():
        script = REPO_ROOT / "skills" / skill_name / "scripts" / "run.py"
        result_path = out_dir / f"{skill_name}-{uuid.uuid4().hex}.json"
        env = dict(os.environ)
        env["AIASE_RESULT_PATH"] = str(result_path)

        proc = subprocess.run(
            [sys.executable, str(script), json.dumps(payload)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert result_path.is_file(), f"{skill_name} did not write AIASE_RESULT_PATH"

        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["task_id"] == payload["task_id"]
        if skill_name == "bug-hunter-YunzhenYang-collection":
            assert result["verdict"] == "clean"
            assert result["bugs"] == []
        if skill_name == "open-sql-result-diff-YunzhenYang-collection":
            assert result["equivalent"] is True
            assert result["diff_type"] == "equivalent"
