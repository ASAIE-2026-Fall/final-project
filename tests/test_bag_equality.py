"""Tests for run_dev.bag_equal — multiset equality on SQL result rows."""

from run_dev import bag_equal


def test_identical_rows():
    a = [(1, "Alice"), (2, "Bob"), (3, "Chen")]
    assert bag_equal(a, a)


def test_order_insensitive():
    a = [(1, "Alice"), (2, "Bob")]
    b = [(2, "Bob"), (1, "Alice")]
    assert bag_equal(a, b)


def test_duplicates_count():
    # "Alice, Bob, Bob" vs "Alice, Bob" must NOT be equal (spec §4.1).
    a = [("Alice",), ("Bob",), ("Bob",)]
    b = [("Alice",), ("Bob",)]
    assert not bag_equal(a, b)


def test_missing_distinct_fail_case():
    # The canonical "missed DISTINCT" example from spec §2.2:
    # student got [(Alice), (Bob), (Bob), (Chen)] but gold is [(Alice), (Bob), (Chen)].
    student = [("Alice",), ("Bob",), ("Bob",), ("Chen",)]
    gold = [("Alice",), ("Bob",), ("Chen",)]
    assert not bag_equal(student, gold)


def test_both_empty():
    assert bag_equal([], [])


def test_one_empty():
    assert not bag_equal([(1,)], [])


def test_none_and_distinct_values():
    a = [(None,), (1,), ("x",)]
    b = [(1,), ("x",), (None,)]
    assert bag_equal(a, b)


def test_lists_accepted_like_tuples():
    a = [[1, "Alice"], [2, "Bob"]]
    b = [(1, "Alice"), (2, "Bob")]
    assert bag_equal(a, b)


def test_column_order_does_not_matter():
    # Updated aiase_contract: row order and column order are ignored, duplicates count.
    a = [("Alice", "CS")]
    b = [("CS", "Alice")]
    assert bag_equal(a, b)


def test_floats_exact():
    a = [(1.5,), (2.25,)]
    b = [(2.25,), (1.5,)]
    assert bag_equal(a, b)


def test_bytes_handled():
    a = [(b"data",)]
    b = [(b"data",)]
    assert bag_equal(a, b)
