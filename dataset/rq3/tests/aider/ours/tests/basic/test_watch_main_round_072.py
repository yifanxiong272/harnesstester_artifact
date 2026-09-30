import sys
import builtins
import types
import pytest

import aider.watch as watch_module


def test_main_round_072(monkeypatch, capsys):
    """Run main() with a patched FileWatcher and controlled argv to exercise
    both the no-change and change branches, then trigger KeyboardInterrupt to
    exercise the cleanup path.

    This covers the argparse path, the inner ignore_test_files definition
    (executed when main() runs), the watcher start/get_changes/stop flow,
    printing of watched directory and changed filenames, and the KeyboardInterrupt
    cleanup branch.
    """

    # Capture created watcher instance so we can assert start/stop were called
    created = []

    class DummyWatcher:
        def __init__(self, directory, gitignores=None):
            # preserve constructor contract: accept directory and gitignores
            self.directory = directory
            self.gitignores = gitignores
            self.started = False
            self.stopped = False
            self.calls = 0
            self.changed_files = None

        def start(self):
            self.started = True

        def get_changes(self):
            # deterministic sequence:
            # 1st call -> no changes (falsy) to exercise the False branch
            # 2nd call -> mapping with two keys to exercise printing and sorting
            # 3rd call -> raise KeyboardInterrupt to exit the loop and exercise cleanup
            self.calls += 1
            if self.calls == 1:
                return {}
            if self.calls == 2:
                # unordered keys to ensure sorting is actually exercised
                return {"b.py": "x", "a.py": "y"}
            raise KeyboardInterrupt

        def stop(self):
            self.stopped = True

    def fake_FileWatcher(directory, gitignores=None):
        inst = DummyWatcher(directory, gitignores=gitignores)
        created.append(inst)
        return inst

    # Patch the FileWatcher symbol where the module resolves it
    monkeypatch.setattr(watch_module, "FileWatcher", fake_FileWatcher)

    # Set deterministic argv: program name, directory, and two --gitignore entries
    monkeypatch.setattr(sys, "argv", ["prog", "srcdir", "--gitignore", "g1", "--gitignore", "g2"]) 

    # Run main and capture stdout; main will raise no exception because we
    # raise KeyboardInterrupt inside DummyWatcher.get_changes which main
    # handles and then calls watcher.stop()
    watch_module.main()

    # Collect printed output
    captured = capsys.readouterr()
    out = captured.out

    # Assertions on printed output
    assert "Watching source files in srcdir..." in out

    # The second get_changes returns keys 'a.py' and 'b.py'; sorted order is a.py then b.py
    # They should each appear on their own line
    assert "a.py\n" in out
    assert "b.py\n" in out

    # The cleanup path prints a newline then 'Stopped watching files'
    assert "Stopped watching files" in out

    # Ensure our fake watcher was constructed and had start() and stop() invoked
    assert len(created) == 1
    watcher_inst = created[0]
    assert watcher_inst.started is True
    assert watcher_inst.stopped is True


if __name__ == "__main__":
    pytest.main([__file__])
