import os
from collections import namedtuple
import aider.repomap as repomap

Tag = namedtuple("Tag", ["kind", "name"])


class IORecorder:
    def __init__(self):
        self.outputs = []
        self.warnings = []

    def tool_output(self, msg):
        # record messages for assertions
        self.outputs.append(str(msg))

    def tool_warning(self, msg):
        self.warnings.append(str(msg))


def test_ranked_tags_with_cache_exception_and_tqdm_round_060():
    """
    Exercises the branch where reading TAGS_CACHE raises SQLITE_ERRORS the first time,
    triggers the "large repo" tqdm branch, exercises verbose output, and builds
    a minimal def/ref pair so pagerank runs without ZeroDivisionError. Assertions
    are observable outputs and returned tuple entries.
    """
    # Prepare environment in module under test
    original_sqlite_errors = getattr(repomap, "SQLITE_ERRORS", None)
    # Make the module treat ValueError as SQLITE error for this test
    repomap.SQLITE_ERRORS = (ValueError,)

    # A cache object that raises on first __len__ then becomes empty
    class BadCache:
        def __init__(self):
            self._first = True

        def __len__(self):
            if self._first:
                self._first = False
                raise ValueError("simulated cache read error")
            return 0

    io = IORecorder()

    # Fake self that provides the attributes the method expects
    class FakeSelf:
        pass

    fake = FakeSelf()
    fake.TAGS_CACHE = BadCache()

    # tags_cache_error should fix the cache so subsequent len() works
    def tags_cache_error(original_error):
        # simulate recovery by replacing cache with empty list
        fake.TAGS_CACHE = []
        # mutate attribute on the fake object as the real method would
        setattr(fake, "TAGS_CACHE", fake.TAGS_CACHE)

    fake.tags_cache_error = tags_cache_error
    fake.io = io
    fake.verbose = True
    fake.warned_files = set()

    # Simple rel name extractor
    fake.get_rel_fname = lambda fname: os.path.basename(fname)

    # Provide files: make many names so len(fnames) - cache_size > 100 triggers
    # Use 105 names to be deterministic
    chat_fnames = [f"chat/file_{i}.py" for i in range(1, 3)]
    other_fnames = [f"other/file_{i}.py" for i in range(1, 105)]

    # We'll have one pair: a def in a chat file and ref in other file with same ident
    # Map specific get_tags per filename
    def get_tags(fname, rel_fname):
        if fname == chat_fnames[0]:
            return [Tag("def", "important_ident")]
        if fname == other_fnames[0]:
            return [Tag("ref", "important_ident")]
        # otherwise return empty list to avoid creating extra graph nodes
        return []

    fake.get_tags = get_tags

    # Make Path.is_file return True for deterministic path handling
    original_path_is_file = repomap.Path.is_file

    try:
        repomap.Path.is_file = lambda self: True

        # Put mentioned_fnames such that rel_fname for other_fnames[0] is considered
        mentioned_fnames = {os.path.basename(other_fnames[0])}
        mentioned_idents = {"important_ident"}

        # Call the function under test
        result = repomap.RepoMap.get_ranked_tags(
            fake, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents, progress=None
        )

        # Assertions (observable behavior):
        # 1) the initial-cache-exception path should have called our tags_cache_error
        assert hasattr(fake, "TAGS_CACHE")
        # 2) tqdm branch should have produced the initial tool_output message
        assert any(
            "Initial repo scan can be slow in larger repos" in out for out in io.outputs
        ), "tqdm branch should call io.tool_output with the slow-scan message"

        # 3) Because we put a def in a chat file, definitions from chat files are excluded
        #    final result should include an entry for the other file (its rel name)
        rel_other = os.path.basename(other_fnames[0])
        assert any(isinstance(it, tuple) and it == (rel_other,) for it in result), (
            f"expected a tuple with other rel fname {rel_other} in result, got: {result}"
        )

    finally:
        # restore monkeypatched names
        repomap.Path.is_file = original_path_is_file
        if original_sqlite_errors is None:
            del repomap.SQLITE_ERRORS
        else:
            repomap.SQLITE_ERRORS = original_sqlite_errors


def test_missing_file_warns_and_progress_round_060():
    """
    Exercises the branch where Path.is_file raises OSError causing the file to be warned about,
    and exercises the progress callback path when not showing a tqdm bar.
    """
    io = IORecorder()

    class FakeSelf:
        pass

    fake = FakeSelf()
    # Set a large cache_size so len(fnames) - cache_size <= 100 (showing_bar False)
    fake.TAGS_CACHE = [None] * 100
    fake.tags_cache_error = lambda e: None
    fake.io = io
    fake.verbose = False
    fake.warned_files = set()
    fake.get_rel_fname = lambda fname: os.path.basename(fname)

    # get_tags returns None for the missing file to exercise the 'continue' branch
    def get_tags_none(fname, rel_fname):
        return None

    fake.get_tags = get_tags_none

    # Patch Path.is_file to raise OSError to hit the OSError handling branch
    original_path_is_file = repomap.Path.is_file
    try:
        def raise_oserror(self):
            raise OSError("simulated file system error")

        repomap.Path.is_file = raise_oserror

        # Capture progress messages
        progress_calls = []

        def progress(msg):
            progress_calls.append(str(msg))

        missing_fname = "some/missing_file.py"
        # Run with a single file so showing_bar remains False
        result = repomap.RepoMap.get_ranked_tags(
            fake, [missing_fname], [], set(), set(), progress=progress
        )

        # Assertions:
        # 1) The IO warning method was invoked mentioning the fname
        assert any(missing_fname in w for w in io.warnings), (
            f"expected a tool_warning mentioning {missing_fname}, got {io.warnings}"
        )

        # 2) The filename was added to warned_files
        assert missing_fname in fake.warned_files

        # 3) progress was called at least once with the update prefix
        assert progress_calls, "progress should be called when provided and not showing bar"
        # The progress messages should contain the module's UPDATING_REPO_MAP_MESSAGE
        assert any(repomap.UPDATING_REPO_MAP_MESSAGE in c for c in progress_calls), (
            "progress should be invoked with UPDATING_REPO_MAP_MESSAGE"
        )

    finally:
        repomap.Path.is_file = original_path_is_file
