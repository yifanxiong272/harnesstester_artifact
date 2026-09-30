# file: rdagent/scenarios/data_science/debug/data.py:472-517
# asked: {"lines": [473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 493, 494, 496, 497, 498, 499, 501, 502, 503, 504, 505, 506, 507, 509, 510, 512, 513, 514, 515, 516, 517], "branches": [[481, 482], [481, 509], [485, 486], [485, 493], [496, 497], [496, 501], [501, 502], [501, 505], [512, 513], [512, 514], [514, 515], [514, 516], [516, 0], [516, 517]]}
# gained: {"lines": [473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 493, 494, 496, 501, 502, 503, 504, 505, 506, 507, 509, 510, 512, 513, 514, 515, 516, 517], "branches": [[481, 482], [485, 486], [485, 493], [496, 501], [501, 502], [501, 505], [512, 513], [512, 514], [514, 515], [514, 516], [516, 0], [516, 517]]}

import os
from pathlib import Path
import pytest

import importlib

DATA_MODULE = importlib.import_module("rdagent.scenarios.data_science.debug.data")
FolderSampler = DATA_MODULE.FolderSampler


class DummyReducer:
    def __init__(self, to_return=None):
        self.calls = []
        self.to_return = to_return

    def reduce(self, items):
        # record items as list of paths
        self.calls.append(list(items))
        if self.to_return is None:
            # default: return items unchanged
            return list(items)
        return list(self.to_return)


def make_file(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_dirs(parent: Path, names):
    paths = []
    for n in names:
        p = parent / n
        p.mkdir(parents=True, exist_ok=True)
        paths.append(p)
    return paths


def _make_sampler(data_folder: Path, sample_folder: Path, reducer):
    # create FolderSampler without calling its real __init__
    sam = object.__new__(FolderSampler)
    sam.data_folder = data_folder
    sam.sample_folder = sample_folder
    sam.data_reducer = reducer
    return sam


def _patch_copy_calls(monkeypatch):
    copied = {"files": [], "folders": []}

    def fake_copy_file(src, sample_folder, data_folder):
        # record string paths to avoid Path objects comparing weirdly
        copied["files"].append((str(src), str(sample_folder), str(data_folder)))

    def fake_copy_folder(src, sample_folder, data_folder):
        copied["folders"].append((str(src), str(sample_folder), str(data_folder)))

    monkeypatch.setattr(DATA_MODULE, "copy_file", fake_copy_file)
    monkeypatch.setattr(DATA_MODULE, "copy_folder", fake_copy_folder)
    return copied


def test_folder_sampler_samples_files_when_no_subdirs(tmp_path, monkeypatch):
    """
    Create a data folder with one subdirectory that contains only files (no deeper subdirs).
    Expect: reducer.reduce called on those files, copy_file called for sample_files and top-level extra files.
    """
    data_folder = tmp_path / "data"
    sample_folder = tmp_path / "sample"
    data_folder.mkdir()
    sample_folder.mkdir()

    # top-level extra file
    top_file = data_folder / "top.txt"
    make_file(top_file, "top")

    # one subdirectory with files (no subdirs)
    sub = data_folder / "dirA"
    sub.mkdir()
    f1 = sub / "a1.txt"
    f2 = sub / "a2.txt"
    make_file(f1, "a1")
    make_file(f2, "a2")

    # prepare reducer to return only one of the subfiles
    reducer = DummyReducer(to_return=[f1])

    sampler = _make_sampler(data_folder, sample_folder, reducer)

    copied = _patch_copy_calls(monkeypatch)

    # Run sample
    sampler.sample()

    # reducer.reduce should have been called once with two files
    assert len(reducer.calls) == 1
    called_with = reducer.calls[0]
    assert set(map(str, called_with)) == {str(f1), str(f2)}

    # copy_file should be called for the sample file and for the top-level extra file
    # Order is not guaranteed; assert both are present
    copied_files = {os.path.basename(t[0]) for t in copied["files"]}
    assert "a1.txt" in copied_files
    assert "top.txt" in copied_files

    # No folders were copied
    assert copied["folders"] == []


def test_folder_sampler_iterates_levels_and_samples_files(tmp_path, monkeypatch):
    """
    Create nested directory structure depth 2 so the code enters the while loop,
    executes the print at line ~493 (when subdirs exist), then descends and samples files
    from the deepest level.
    """
    data_folder = tmp_path / "data2"
    sample_folder = tmp_path / "sample2"
    data_folder.mkdir()
    sample_folder.mkdir()

    # Top-level directories
    dir1 = data_folder / "dir1"
    dir2 = data_folder / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Each top-level dir has one subdir (so subdirs is non-empty on first iteration)
    sub1 = dir1 / "sub1"
    sub2 = dir2 / "sub2"
    sub1.mkdir()
    sub2.mkdir()

    # Put files only in the deepest subdirs
    deep_file1 = sub1 / "deep1.txt"
    deep_file2 = sub2 / "deep2.txt"
    make_file(deep_file1, "d1")
    make_file(deep_file2, "d2")

    # Also add a top-level extra file to verify extra_files handling
    top_extra = data_folder / "extra_root.txt"
    make_file(top_extra, "root")

    reducer = DummyReducer()  # return items unchanged

    sampler = _make_sampler(data_folder, sample_folder, reducer)

    copied = _patch_copy_calls(monkeypatch)

    sampler.sample()

    # reducer.reduce should have been called once (on the two deep files)
    # The deep files are found when descending to the subdirs level
    assert len(reducer.calls) == 1
    got = {os.path.basename(p) for p in reducer.calls[0]}
    assert got == {"deep1.txt", "deep2.txt"}

    # copy_file should be called for the two deep files and for the top-level extra file
    copied_files = {os.path.basename(t[0]) for t in copied["files"]}
    assert "deep1.txt" in copied_files
    assert "deep2.txt" in copied_files
    assert "extra_root.txt" in copied_files

    # No folders copied in this scenario
    assert copied["folders"] == []


def test_folder_sampler_samples_many_subdirs_triggers_reduce_for_dirs(tmp_path, monkeypatch):
    """
    Create one directory that contains >100 subdirectories so the condition
    len(subdirs_names) > 100 triggers and reducer.reduce is called on subdirs,
    after which copy_folder should be invoked for the sampled folders.
    """
    data_folder = tmp_path / "data3"
    sample_folder = tmp_path / "sample3"
    data_folder.mkdir()
    sample_folder.mkdir()

    # One top-level directory that contains many subdirs
    big = data_folder / "big"
    big.mkdir()

    # create 101 subdirectories inside 'big'
    many = make_dirs(big, [f"s{i}" for i in range(101)])

    # Put a file inside one of them to make them non-empty (not strictly necessary)
    make_file(many[0] / "file.txt", "x")

    # Reducer will select a subset (e.g., first 3 folders)
    selected = many[:3]
    reducer = DummyReducer(to_return=selected)

    sampler = _make_sampler(data_folder, sample_folder, reducer)

    copied = _patch_copy_calls(monkeypatch)

    sampler.sample()

    # reducer.reduce should have been called once with the 101 subdirs
    assert len(reducer.calls) == 1
    called_with = reducer.calls[0]
    assert len(called_with) == 101
    # copy_folder should be called for each selected folder
    copied_folders = {os.path.basename(t[0]) for t in copied["folders"]}
    assert copied_folders == {p.name for p in selected}

    # There may be extra_files (none in this case), ensure no file copies happened
    # (except possibly files from selected folders if reducer returned folders; our reducer returns folders)
    # We only assert that folder copies happened
    assert len(copied["folders"]) == len(selected)
