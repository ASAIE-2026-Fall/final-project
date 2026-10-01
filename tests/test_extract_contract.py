"""Tests for run_dev.extract_last_json_block — single source of truth for output contract parsing."""

from run_dev import extract_last_json_block


def test_basic_single_block():
    s = '''some preface
```json
{"task_id": "x", "sql": "SELECT 1"}
```
'''
    obj = extract_last_json_block(s)
    assert obj == {"task_id": "x", "sql": "SELECT 1"}


def test_multiple_blocks_takes_last():
    s = '''first attempt:
```json
{"task_id": "x", "sql": "SELECT bad"}
```
revision:
```json
{"task_id": "x", "sql": "SELECT good"}
```
'''
    obj = extract_last_json_block(s)
    assert obj == {"task_id": "x", "sql": "SELECT good"}


def test_no_fence_returns_none():
    assert extract_last_json_block("just prose, no JSON") is None
    assert extract_last_json_block("```python\nprint(1)\n```") is None


def test_invalid_json_returns_none():
    s = "```json\n{not valid json,}\n```"
    assert extract_last_json_block(s) is None


def test_non_object_top_level_returns_none():
    # array at top-level violates spec §1.4 #1
    s = '```json\n[1, 2, 3]\n```'
    assert extract_last_json_block(s) is None
    # plain string also rejected
    s2 = '```json\n"hello"\n```'
    assert extract_last_json_block(s2) is None


def test_case_insensitive_fence():
    s = '```JSON\n{"ok": true}\n```'
    assert extract_last_json_block(s) == {"ok": True}


def test_crlf_line_endings():
    s = "preface\r\n```json\r\n{\"k\": 1}\r\n```\r\n"
    assert extract_last_json_block(s) == {"k": 1}


def test_unicode_content():
    s = '```json\n{"name": "陳小明", "rationale": "中文 OK"}\n```'
    obj = extract_last_json_block(s)
    assert obj["name"] == "陳小明"


def test_none_input():
    assert extract_last_json_block(None) is None  # type: ignore[arg-type]
    assert extract_last_json_block(123) is None  # type: ignore[arg-type]
