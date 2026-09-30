# file: sweagent/inspector/server.py:37-48
# asked: {"lines": [37, 38, 39, 40, 41, 42, 43, 44, 45, 48], "branches": [[38, 39], [38, 48], [39, 40], [39, 48]]}
# gained: {"lines": [37, 38, 39, 40, 41, 42, 43, 44, 45, 48], "branches": [[38, 39], [38, 48], [39, 40], [39, 48]]}

import copy
import pytest

from sweagent.inspector.server import append_patch


def test_append_patch_appends_when_exit_status_and_patch_present():
    instance_id = "instance-1"
    patch_text = "diff --git a/file b/file\n@@ -1 +1 @@\n-foo\n+bar\n"
    content = {
        "info": {"exit_status": 0},
        "trajectory": [],
    }
    patches = {instance_id: patch_text}
    patch_type = "Diff"

    returned = append_patch(instance_id, content, patches, patch_type)

    # function should return the same object (mutated in place)
    assert returned is content

    # trajectory should have exactly one appended element
    assert len(content["trajectory"]) == 1
    appended = content["trajectory"][0]

    # verify the appended structure and values
    assert appended["thought"] == f"Showing {patch_type} patch"
    assert appended["response"] == f"Showing {patch_type} patch"
    assert appended["action"] == f"{patch_type} Patch"
    assert appended["observation"] == patch_text


def test_append_patch_no_append_when_exit_status_is_none_or_missing():
    instance_id = "instance-2"
    patch_text = "patch-irrelevant"
    # Case A: exit_status explicitly None
    content_a = {"info": {"exit_status": None}, "trajectory": []}
    patches = {instance_id: patch_text}
    returned_a = append_patch(instance_id, content_a, patches, "PatchType")
    assert returned_a is content_a
    assert content_a["trajectory"] == []

    # Case B: info key missing entirely
    content_b = {"trajectory": []}
    returned_b = append_patch(instance_id, content_b, patches, "PatchType")
    assert returned_b is content_b
    assert content_b["trajectory"] == []


def test_append_patch_no_append_when_patch_missing_even_if_exit_status_present():
    instance_id = "instance-3"
    content = {"info": {"exit_status": 1}, "trajectory": []}
    patches = {}  # no entry for instance_id
    returned = append_patch(instance_id, content, patches, "Fix")

    assert returned is content
    # Should not append since instance_id not in patches
    assert content["trajectory"] == []
