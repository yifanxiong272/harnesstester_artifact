# file: aider/coders/search_replace.py:338-403
# asked: {"lines": [339, 342, 343, 345, 347, 348, 351, 352, 353, 354, 356, 357, 358, 360, 361, 362, 364, 365, 366, 368, 369, 370, 372, 373, 374, 376, 378, 379, 380, 382, 383, 385, 386, 388, 389, 391, 393, 395, 396, 400, 401, 403], "branches": [[342, 343], [342, 345], [378, 379], [378, 388], [385, 386], [385, 388], [393, 395], [393, 400], [400, 401], [400, 403]]}
# gained: {"lines": [339, 342, 343, 345, 347, 348, 351, 352, 353, 354, 356, 357, 358, 360, 361, 362, 364, 365, 366, 368, 369, 370, 372, 373, 374, 376, 378, 388, 389, 391, 393, 400, 401, 403], "branches": [[342, 343], [342, 345], [378, 388], [393, 400], [400, 401], [400, 403]]}

import pytest

import aider.coders.search_replace as sr

class FakeDMP:
    def __init__(self, mode="success"):
        # attributes that the real code sets
        self.Diff_Timeout = None
        self.Match_Threshold = None
        self.Match_Distance = None
        self.Match_MaxBits = None
        self.Patch_Margin = None
        self._mode = mode
        self._mapping = None

    def diff_linesToChars(self, all_text, _empty):
        # Map identical lines to the same token character, like the real implementation.
        lines = all_text.splitlines()
        mapping = {}
        token_for_line = {}
        next_code = 1
        chars = []
        for line in lines:
            if line not in token_for_line:
                ch = chr(next_code)
                next_code += 1
                token_for_line[line] = ch
                mapping[ord(ch)] = line + "\n"
            chars.append(token_for_line[line])
        all_chars = "".join(chars)
        self._mapping = mapping
        return all_chars, None, mapping

    def diff_main(self, search_lines, replace_lines, _):
        # store for patch_make
        self._search_lines = search_lines
        self._replace_lines = replace_lines
        # Return a dummy diff; not used by our patch_make
        return [("DUMMY", None)]

    def diff_cleanupSemantic(self, diff_lines):
        pass

    def diff_cleanupEfficiency(self, diff_lines):
        pass

    def patch_make(self, search_lines, diff_lines):
        # Return a simple tuple containing search and replace tokens
        return (self._search_lines, self._replace_lines)

    def patch_apply(self, patches, original_lines):
        search_tokens, replace_tokens = patches
        if self._mode == "success":
            count = original_lines.count(search_tokens)
            if count == 0:
                # no application possible -> indicate failure
                return original_lines, [False]
            new_lines = original_lines.replace(search_tokens, replace_tokens)
            successes = [True] * count
            return new_lines, successes
        else:
            # simulate failed patch application
            return original_lines, [False]

def test_dmp_lines_apply_success(monkeypatch):
    # Arrange: replace diff_match_patch with our FakeDMP that will succeed
    monkeypatch.setattr(sr, "diff_match_patch", lambda: FakeDMP(mode="success"))
    search_text = "foo\n"
    replace_text = "bar\n"
    original_text = "foo\nbaz\n"
    # Act
    result = sr.dmp_lines_apply([search_text, replace_text, original_text])
    # Assert
    assert isinstance(result, str)
    assert result == "bar\nbaz\n"
    assert result.endswith("\n")

def test_dmp_lines_apply_failure(monkeypatch):
    # Arrange: replace diff_match_patch with our FakeDMP that will simulate failure
    monkeypatch.setattr(sr, "diff_match_patch", lambda: FakeDMP(mode="fail"))
    search_text = "nope\n"
    replace_text = "something\n"
    original_text = "foo\nbar\n"
    # Act
    result = sr.dmp_lines_apply([search_text, replace_text, original_text])
    # Assert: when patches fail, function returns None
    assert result is None
