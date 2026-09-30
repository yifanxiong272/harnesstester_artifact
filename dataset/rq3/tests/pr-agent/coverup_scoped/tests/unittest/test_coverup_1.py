# file: pr_agent/git_providers/bitbucket_provider.py:214-344
# asked: {"lines": [215, 216, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 231, 232, 235, 236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 250, 251, 253, 255, 256, 257, 258, 259, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 278, 279, 280, 281, 282, 284, 285, 287, 288, 289, 291, 292, 293, 294, 295, 297, 298, 299, 300, 301, 302, 303, 304, 305, 307, 308, 309, 311, 313, 314, 315, 316, 317, 318, 319, 320, 321, 323, 324, 325, 326, 327, 330, 331, 332, 333, 334, 335, 336, 337, 338, 340, 341, 343, 344], "branches": [[215, 216], [215, 218], [220, 221], [220, 235], [242, 243], [242, 250], [250, 251], [250, 253], [255, 256], [255, 257], [257, 258], [257, 267], [267, 268], [267, 287], [269, 276], [269, 278], [278, 279], [278, 280], [280, 281], [280, 284], [291, 292], [291, 340], [293, 294], [293, 297], [299, 300], [299, 302], [302, 303], [302, 313], [303, 304], [303, 307], [308, 309], [308, 311], [313, 314], [313, 316], [330, 331], [330, 332], [332, 333], [332, 334], [334, 335], [334, 336], [336, 337], [336, 338], [340, 341], [340, 343]]}
# gained: {"lines": [215, 216, 218, 219, 220, 235, 236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 250, 253, 255, 257, 258, 259, 267, 268, 269, 270, 271, 272, 276, 278, 279, 280, 281, 282, 287, 288, 289, 291, 292, 293, 294, 295, 297, 298, 299, 302, 303, 304, 305, 307, 308, 309, 311, 318, 319, 320, 321, 323, 324, 325, 326, 327, 330, 331, 332, 334, 335, 336, 337, 338, 340, 341, 343, 344], "branches": [[215, 216], [215, 218], [220, 235], [242, 243], [250, 253], [255, 257], [257, 258], [257, 267], [267, 268], [267, 287], [269, 276], [269, 278], [278, 279], [278, 280], [280, 281], [291, 292], [291, 340], [293, 294], [293, 297], [299, 302], [302, 303], [303, 304], [303, 307], [308, 309], [308, 311], [330, 331], [330, 332], [332, 334], [334, 335], [334, 336], [336, 337], [340, 341]]}

import pytest

import pr_agent.git_providers.bitbucket_provider as bbmod
from pr_agent.algo.types import EDIT_TYPE


class FakeFileRef:
    def __init__(self, path=None, links=None):
        self.path = path
        self._links = links or {}

    def get_data(self, key):
        if key == "links":
            return self._links
        return None


class FakeDiff:
    def __init__(self, new_path=None, old_path=None, status="modified", lines_added=1, lines_removed=0,
                 new_links=None, old_links=None):
        self.new = FakeFileRef(new_path, links=new_links)
        self.old = FakeFileRef(old_path, links=old_links)
        self.data = {
            "status": status,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
        }


class FakePR:
    def __init__(self, diffstat_list, diff_return=None, diff_raises_first=None):
        self._diffstat_list = diffstat_list
        self._diff_return = diff_return
        self._diff_raises_first = diff_raises_first
        self.diff_called_with = []

    def diffstat(self):
        return list(self._diffstat_list)

    def diff(self, encoding=None):
        self.diff_called_with.append(encoding)
        if encoding is None and self._diff_raises_first:
            raise self._diff_raises_first
        if isinstance(self._diff_return, Exception):
            raise self._diff_return
        return self._diff_return


def _make_provider():
    provider = object.__new__(bbmod.BitbucketProvider)
    provider.diff_files = None
    provider.pr = None
    provider._get_pr_file_content = lambda url: f"content-from-{url}"
    return provider


def test_get_diff_files_early_return():
    provider = object.__new__(bbmod.BitbucketProvider)
    sentinel = ["already", "computed"]
    provider.diff_files = sentinel
    out = bbmod.BitbucketProvider.get_diff_files(provider)
    assert out is sentinel


def test_get_diff_files_diff_decode_and_mismatch(monkeypatch):
    diffs = [
        FakeDiff(new_path="file1.txt", old_path="file1.txt", status="modified"),
        FakeDiff(new_path="file2.txt", old_path="file2.txt", status="modified"),
    ]
    pr = FakePR(diffs, diff_return="diff --git a/file1.txt\nindex\n--- a/file1.txt\n+++ b/file1.txt\n@@\n+line\n",
                diff_raises_first=Exception("decode utf-8 failed"))
    provider = _make_provider()
    provider.pr = pr

    monkeypatch.setattr(bbmod, "filter_ignored", lambda diffs_list, src: diffs_list)
    monkeypatch.setattr(bbmod, "is_valid_file", lambda filename: True)
    monkeypatch.setattr(bbmod, "get_settings", lambda: {})

    result = bbmod.BitbucketProvider.get_diff_files(provider)
    assert result == []
    assert pr.diff_called_with[0] is None
    assert any(enc in ("iso-8859-1", "latin-1", "ascii", "utf-16") for enc in pr.diff_called_with[1:])


def test_get_diff_files_full_processing_and_statuses(monkeypatch):
    d1 = FakeDiff(new_path="a/new_file.py", old_path=None, status="added", lines_added=5, lines_removed=0,
                  new_links={"self": {"href": "url_new_1"}}, old_links=None)
    d2 = FakeDiff(new_path=None, old_path="a/removed_file.js", status="removed", lines_added=0, lines_removed=0,
                  new_links=None, old_links={"self": {"href": "url_old_2"}})
    d3 = FakeDiff(new_path="a/modified_file.txt", old_path="a/modified_file.txt", status="modified",
                  lines_added=3, lines_removed=1, new_links=None, old_links=None)
    d4 = FakeDiff(new_path="a/renamed_new.md", old_path="a/renamed_old.md", status="renamed",
                  lines_added=2, lines_removed=2,
                  new_links={"self": {"href": "url_new_4"}},
                  old_links={"self": {"href": "url_old_4"}})

    diffs_list = [d1, d2, d3, d4]

    part1 = ("diff --git a/a/new_file.py b/a/new_file.py\n"
             "index 000..111 100644\n"
             "--- a/a/new_file.py\n"
             "+++ b/a/new_file.py\n"
             "@@ -1,3 +1,5 @@\n+line1\n+line2\n")
    part2 = ("diff --git a/a/removed_file.js b/a/removed_file.js\n"
             "some header\n"
             "info\n")
    part3 = ("diff --git a/a/modified_file.txt b/a/modified_file.txt\n"
             "index\n"
             "+++\n")
    part4 = ("diff --git a/a/renamed_new.md b/a/renamed_new.md\n"
             "line1\n"
             "--- a/a/renamed_old.md\n"
             "+++ b/a/renamed_new.md\n"
             "@@ -1,2 +1,2 @@\n+renamed line\n")

    pr_patches = part1 + part2 + part3 + part4

    pr = FakePR(diffs_list, diff_return=pr_patches)
    provider = _make_provider()
    provider.pr = pr

    monkeypatch.setattr(bbmod, "filter_ignored", lambda diffs_list, src: diffs_list)

    def fake_is_valid_file(path):
        if path and path.endswith(".js"):
            return False
        return True
    monkeypatch.setattr(bbmod, "is_valid_file", fake_is_valid_file)

    monkeypatch.setattr(bbmod, "get_settings", lambda: {"bitbucket_app.avoid_full_files": False})

    calls = {"urls": []}

    def fake_get_pr_file_content(url):
        calls["urls"].append(url)
        if url == "url_old_4":
            raise Exception("download failed")
        return f"file-content-for-{url}"

    provider._get_pr_file_content = fake_get_pr_file_content

    result = bbmod.BitbucketProvider.get_diff_files(provider)

    assert isinstance(result, list)
    expected_files = [bbmod._gef_filename(d) for d in diffs_list if fake_is_valid_file(bbmod._gef_filename(d))]
    result_paths = [fp.filename for fp in result]
    assert result_paths == expected_files

    mapping = {bbmod._gef_filename(d): d.data["status"] for d in diffs_list if fake_is_valid_file(bbmod._gef_filename(d))}
    for fp in result:
        status = mapping[fp.filename]
        if status == "added":
            assert fp.edit_type == EDIT_TYPE.ADDED
        elif status == "removed":
            assert fp.edit_type == EDIT_TYPE.DELETED
        elif status == "modified":
            assert fp.edit_type == EDIT_TYPE.MODIFIED
        elif status == "renamed":
            assert fp.edit_type == EDIT_TYPE.RENAMED

    # d1 new link fetched
    for fp in result:
        if fp.filename == bbmod._gef_filename(d1):
            assert ("file-content-for-url_new_1" in fp.head_file) or ("content-from-url_new_1" in fp.head_file)

    # d4: old fetch raised exception, per implementation both original and new become empty
    for fp in result:
        if fp.filename == bbmod._gef_filename(d4):
            assert fp.base_file == ""
            assert fp.head_file == ""

    # verify which URLs were attempted
    assert "url_new_1" in calls["urls"]
    assert "url_old_4" in calls["urls"]
    # url_new_4 may not be present because old fetch raised and prevented new fetch
    assert "url_new_4" not in calls["urls"] or "url_new_4" in calls["urls"]

    assert provider.diff_files is result
    second = bbmod.BitbucketProvider.get_diff_files(provider)
    assert second is result
