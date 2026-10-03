def test_probe_001():
    import aider.repomap as repomap
    from aider.repomap import RepoMap

    # Save originals to restore after the test
    orig_filename_to_lang = getattr(repomap, "filename_to_lang", None)
    orig_get_scm_fname = getattr(repomap, "get_scm_fname", None)
    orig_get_parser = getattr(repomap, "get_parser", None)
    orig_get_language = getattr(repomap, "get_language", None)
    orig_Query = getattr(repomap, "Query", None)
    orig_using = getattr(repomap, "USING_TSL_PACK", None)
    orig_run = getattr(RepoMap, "_run_captures", None)

    try:
        # Deterministic module-level helpers
        repomap.filename_to_lang = lambda fname: "py"

        class _SCM:
            def exists(self):
                return True

            def read_text(self):
                return "query"

        repomap.get_scm_fname = lambda lang: _SCM()

        class _Parser:
            @staticmethod
            def parse(b):
                # Return minimal object with root_node; our fake _run_captures ignores it
                return type("_T", (), {"root_node": None})()

        repomap.get_parser = lambda lang: _Parser()
        repomap.get_language = lambda lang: "lang"
        # Avoid constructing the real Query object; supply a harmless placeholder
        repomap.Query = lambda language, q: (language, q)

        # Force the branch that builds all_nodes from captures_by_tag (exposes duplicate append bug)
        repomap.USING_TSL_PACK = True

        # Create two distinct fake node-like objects used by get_tags_raw
        class FakeNode:
            def __init__(self, name_bytes, line):
                self.text = name_bytes
                self.start_point = (line, 0)

        node1 = FakeNode(b"name1", 10)
        node2 = FakeNode(b"name2", 20)

        # Provide a deterministic _run_captures that returns two nodes under the same tag
        def fake_run_captures(self, query, root_node):
            return {"name.definition.test": [node1, node2]}

        RepoMap._run_captures = fake_run_captures

        # Construct a RepoMap instance without invoking its real constructor
        repo = RepoMap.__new__(RepoMap)

        class IO:
            def read_text(self, fname):
                return "some code"

        repo.io = IO()

        # Execute the target entrypoint
        results = list(repo.get_tags_raw("/path/to/file.py", "rel/file.py"))

        # Observe the externally visible Tag tuples
        observed = [(t.name, t.kind, t.line) for t in results]
        expected = [("name1", "def", 10), ("name2", "def", 20)]

        # Primary oracle: exactly the two distinct Tag objects, no duplicates
        assert len(results) == 2 and set(observed) == set(expected), (
            f"get_tags_raw yielded tags {observed}, expected exactly {expected} (no duplicates)"
        )
    finally:
        # Restore module state
        if orig_filename_to_lang is None:
            try:
                delattr(repomap, "filename_to_lang")
            except Exception:
                pass
        else:
            repomap.filename_to_lang = orig_filename_to_lang

        if orig_get_scm_fname is None:
            try:
                delattr(repomap, "get_scm_fname")
            except Exception:
                pass
        else:
            repomap.get_scm_fname = orig_get_scm_fname

        if orig_get_parser is None:
            try:
                delattr(repomap, "get_parser")
            except Exception:
                pass
        else:
            repomap.get_parser = orig_get_parser

        if orig_get_language is None:
            try:
                delattr(repomap, "get_language")
            except Exception:
                pass
        else:
            repomap.get_language = orig_get_language

        if orig_Query is None:
            try:
                delattr(repomap, "Query")
            except Exception:
                pass
        else:
            repomap.Query = orig_Query

        if orig_using is None:
            try:
                delattr(repomap, "USING_TSL_PACK")
            except Exception:
                pass
        else:
            repomap.USING_TSL_PACK = orig_using

        if orig_run is None:
            try:
                delattr(RepoMap, "_run_captures")
            except Exception:
                pass
        else:
            RepoMap._run_captures = orig_run
