def test_probe_001():
    # Import the target module and the entrypoint method
    from aider import repomap as repomap_mod

    # Prepare deterministic fake node matching the shape used by get_tags_raw
    class FakeNode:
        def __init__(self, text, start_point):
            self.text = text
            self.start_point = start_point

    node = FakeNode(b"foo", (3, 5))

    # Fake _run_captures returns a mapping with one tag and exactly one node
    captures = {"name.definition.foo": [node]}

    # Build a fake self object with minimal attributes used by get_tags_raw
    class FakeIO:
        def read_text(self, fname):
            return "some code content"

    class FakeSelf:
        pass

    fake = FakeSelf()
    fake.io = FakeIO()

    def fake_run_captures(query, root_node):
        # ignore arguments; return the prepared captures mapping
        return captures

    fake._run_captures = fake_run_captures

    # Monkeypatch required module-level functions/values in aider.repomap
    # Save originals to avoid surprising side-effects in the test environment
    _orig_filename_to_lang = repomap_mod.filename_to_lang
    _orig_get_language = repomap_mod.get_language
    _orig_get_parser = repomap_mod.get_parser
    _orig_get_scm_fname = repomap_mod.get_scm_fname
    _orig_Query = getattr(repomap_mod, "Query", None)
    _orig_Tag = getattr(repomap_mod, "Tag", None)
    _orig_guess_lexer_for_filename = getattr(repomap_mod, "guess_lexer_for_filename", None)
    _orig_USING_TSL_PACK = getattr(repomap_mod, "USING_TSL_PACK", None)

    try:
        # filename_to_lang must return a non-empty identifier
        repomap_mod.filename_to_lang = lambda fname: "py"

        # get_language and get_parser should succeed; parser.parse must return an object with root_node
        repomap_mod.get_language = lambda lang: "FAKE_LANG"

        class FakeParser:
            class Tree:
                def __init__(self):
                    self.root_node = object()

            def parse(self, b):
                return FakeParser.Tree()

        repomap_mod.get_parser = lambda lang: FakeParser()

        # get_scm_fname should return an object whose exists() is True and read_text() gives a query string
        class FakeSCM:
            def exists(self):
                return True

            def read_text(self):
                return "(dummy query)"

        repomap_mod.get_scm_fname = lambda lang: FakeSCM()

        # Use a trivial Query placeholder; get_tags_raw only passes it to _run_captures
        class DummyQuery:
            def __init__(self, language, query_text):
                self.language = language
                self.query_text = query_text

        repomap_mod.Query = DummyQuery

        # Provide a lightweight Tag class used to create yielded results
        class SimpleTag:
            def __init__(self, rel_fname, fname, name, kind, line):
                self.rel_fname = rel_fname
                self.fname = fname
                self.name = name
                self.kind = kind
                self.line = line

            def __repr__(self):
                return f"Tag(name={self.name!r}, kind={self.kind!r}, line={self.line!r})"

        repomap_mod.Tag = SimpleTag

        # Force USING_TSL_PACK to True so all_nodes is built from captures_by_tag
        repomap_mod.USING_TSL_PACK = True

        # Make guess_lexer_for_filename raise so the function does not attempt backfill (we want only the captured tags)
        def raise_lexer(fname, code):
            raise Exception("no lexer available")

        repomap_mod.guess_lexer_for_filename = raise_lexer

        # Call the entrypoint method directly on the class, supplying our fake self
        fname = "some_file.py"
        rel_fname = "some_file.py"

        results = list(repomap_mod.RepoMap.get_tags_raw(fake, fname, rel_fname))

        # Primary oracle: exactly one Tag produced, with expected properties
        assert len(results) == 1, f"expected exactly 1 Tag, got {len(results)}: {results}"
        tag = results[0]
        assert tag.kind == "def", f"expected kind 'def', got {tag.kind}"
        assert tag.name == "foo", f"expected name 'foo', got {tag.name}"
        assert tag.line == node.start_point[0], f"expected line {node.start_point[0]}, got {tag.line}"
    finally:
        # Restore originals
        repomap_mod.filename_to_lang = _orig_filename_to_lang
        repomap_mod.get_language = _orig_get_language
        repomap_mod.get_parser = _orig_get_parser
        repomap_mod.get_scm_fname = _orig_get_scm_fname
        if _orig_Query is not None:
            repomap_mod.Query = _orig_Query
        if _orig_Tag is not None:
            repomap_mod.Tag = _orig_Tag
        repomap_mod.guess_lexer_for_filename = _orig_guess_lexer_for_filename
        repomap_mod.USING_TSL_PACK = _orig_USING_TSL_PACK
