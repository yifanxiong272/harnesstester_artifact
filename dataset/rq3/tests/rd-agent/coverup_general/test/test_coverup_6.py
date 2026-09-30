# file: rdagent/scenarios/data_science/debug/data.py:321-464
# asked: {"lines": [324, 325, 326, 327, 328, 329, 331, 332, 333, 334, 336, 337, 338, 340, 341, 342, 343, 345, 346, 348, 349, 351, 354, 355, 356, 357, 358, 359, 361, 362, 363, 366, 367, 369, 370, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 386, 387, 388, 389, 390, 391, 392, 393, 396, 397, 398, 399, 400, 401, 404, 406, 407, 408, 410, 412, 413, 414, 415, 418, 419, 422, 423, 424, 426, 429, 430, 431, 432, 433, 434, 435, 437, 438, 440, 443, 444, 448, 450, 451, 452, 453, 454, 457, 458, 459, 461, 462, 463], "branches": [[327, 328], [327, 331], [340, 341], [340, 386], [342, 343], [342, 345], [345, 346], [345, 348], [348, 349], [348, 351], [354, 355], [354, 361], [355, 340], [355, 356], [362, 363], [362, 366], [372, 373], [372, 374], [374, 375], [374, 379], [375, 374], [375, 376], [379, 340], [379, 380], [388, 389], [388, 396], [389, 390], [389, 391], [398, 399], [398, 461], [404, 405], [404, 418], [405, 410], [405, 412], [412, 413], [412, 415], [413, 412], [413, 414], [418, 419], [418, 422], [422, 423], [422, 457], [423, 424], [423, 426], [431, 432], [431, 440], [432, 433], [432, 434], [434, 435], [434, 437], [448, 450], [448, 457], [451, 452], [451, 453], [458, 398], [458, 459]]}
# gained: {"lines": [324, 325, 326, 327, 328, 329, 331, 332, 333, 334, 336, 337, 338, 340, 341, 342, 345, 348, 349, 351, 354, 355, 356, 357, 358, 359, 361, 362, 366, 367, 369, 370, 372, 374, 375, 379, 380, 381, 382, 383, 386, 387, 388, 389, 390, 391, 392, 393, 396, 397, 398, 399, 400, 401, 404, 406, 407, 408, 412, 413, 414, 415, 418, 422, 423, 424, 426, 429, 430, 431, 432, 433, 434, 435, 437, 438, 440, 443, 444, 448, 450, 451, 452, 453, 454, 457, 458, 459, 461, 462, 463], "branches": [[327, 328], [327, 331], [340, 341], [340, 386], [342, 345], [345, 348], [348, 349], [348, 351], [354, 355], [354, 361], [355, 340], [355, 356], [362, 366], [372, 374], [374, 375], [374, 379], [375, 374], [379, 380], [388, 389], [388, 396], [389, 390], [389, 391], [398, 399], [398, 461], [404, 405], [404, 418], [405, 412], [412, 413], [412, 415], [413, 412], [413, 414], [418, 422], [422, 423], [423, 424], [423, 426], [431, 432], [431, 440], [432, 433], [432, 434], [434, 435], [434, 437], [448, 450], [448, 457], [451, 452], [451, 453], [458, 398], [458, 459]]}

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _make_copy_file(data_folder: Path, sample_folder: Path):
    def _copy_file(src: Path, sample_folder_arg: Path, data_folder_arg: Path):
        # Reconstruct the target similar to the implementation under test
        target = sample_folder_arg / src.relative_to(data_folder_arg)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)
    return _copy_file


def _count_files_in_folder_factory(files):
    # returns a function that counts suffixes from given files list (Paths)
    def _count_files_in_folder(files_to_process):
        cnt = {}
        for f in files_to_process:
            cnt.setdefault(f.suffix.lower(), 0)
            cnt[f.suffix.lower()] += 1
        # Force .txt to be considered "rare" so extra files logic triggers
        cnt[".txt"] = cnt.get(".txt", 0)
        return cnt
    return _count_files_in_folder


def _make_dummy_dataframe(cols, rows=3):
    # Create a simple DataFrame for testing
    data = {}
    for c in cols:
        data[c] = [f"{c}_{i}" for i in range(rows)]
    return pd.DataFrame(data)


def _setup_sampler_instance(module, tmp_path, *, data_reducer, data_handler, included_extensions):
    DefaultSampler = module.DefaultSampler
    sampler = object.__new__(DefaultSampler)
    sampler.data_folder = tmp_path / "data"
    sampler.sample_folder = tmp_path / "sample"
    sampler.data_reducer = data_reducer
    sampler.data_handler = data_handler
    sampler.included_extensions = set(included_extensions)
    # Ensure folders exist
    sampler.data_folder.mkdir(parents=True, exist_ok=True)
    sampler.sample_folder.mkdir(parents=True, exist_ok=True)
    return sampler


def test_default_sampler_non_json_sampling(tmp_path, monkeypatch):
    """
    Test the sampling behavior when data_reducer is not a JsonReducer.
    This exercises:
    - processing of files (load, reduce, dump)
    - skipping subfolder data when 'train*' file exists at root
    - selection of files to copy when no used files are present
    - copying of extra files based on count_files_in_folder logic
    - the final counting of sample folder files
    """
    import rdagent.scenarios.data_science.debug.data as data_mod

    # Create a realistic folder structure
    data_root = tmp_path / "data"
    images = data_root / "images"
    docs = data_root / "docs"
    data_root.mkdir()
    images.mkdir()
    docs.mkdir()

    # Root train file to trigger skip_subfolder_data=True
    train_csv = data_root / "train.csv"
    train_csv.write_text("a,b\n1,2\n3,4\n")

    # Files in subfolders that should be considered in the later phase
    (images / "img1.jpg").write_text("jpg1")
    (images / "img2.png").write_text("png2")
    (images / "groupA.txt").write_text("txtA")
    (docs / "doc1.txt").write_text("doc1")
    (docs / "doc2.txt").write_text("doc2")
    (docs / "doc2.csv").write_text("doc2csv")

    # Prepare a data_handler that loads a DataFrame for train.csv and can dump
    class DummyHandler:
        def load(self, path):
            # Only load CSVs for test; return None for others
            if path.suffix.lower() == ".csv":
                # create a dataframe with a non-id column to force path leading to not_used_files
                return _make_dummy_dataframe(["label", "value"], rows=2)
            return None

        def dump(self, df, target_path):
            # Dump as CSV to mimic behavior
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(df.to_csv(index=False))

    # Prepare a data_reducer that simply returns a reduced dataframe
    class DummyReducer:
        def __init__(self):
            self.sampled_files = []
            self.min_num = 1
            self.min_frac = 0.5

        def reduce(self, df):
            # Return a small subset (first row)
            return df.head(1)

    dummy_reducer = DummyReducer()
    dummy_handler = DummyHandler()

    # Build sampler instance
    sampler = _setup_sampler_instance(
        data_mod, tmp_path,
        data_reducer=dummy_reducer, data_handler=dummy_handler,
        included_extensions={".csv", ".txt", ".jpg", ".png"}
    )

    # Monkeypatch helpers used in the module
    # count_files_in_folder will reflect the actual file types but leave .txt as small count
    all_files = list(data_root.rglob("*"))
    monkeypatch.setattr(data_mod, "count_files_in_folder", _count_files_in_folder_factory(all_files))
    # copy_file should behave like a normal copy with relative path preservation
    monkeypatch.setattr(data_mod, "copy_file", _make_copy_file(data_root, sampler.sample_folder))

    # Ensure deterministic shuffling
    np.random.seed(0)

    # Run the sample method
    sampler.sample()

    # Assert that sample folder has files copied: at least one from docs/images should be present
    sampled_files = [p for p in sampler.sample_folder.rglob("*") if p.is_file()]
    assert len(sampled_files) > 0, "No files were sampled/copied into the sample folder"

    # Ensure the train.csv processed file was dumped into sample folder as well
    expected_train = sampler.sample_folder / train_csv.relative_to(data_root)
    assert expected_train.exists(), "Processed root CSV (train.csv) should be dumped into the sample folder"

    # Ensure that at least one extra .txt file was copied due to extra_tag logic
    txts_in_sample = [p for p in sampled_files if p.suffix.lower() == ".txt"]
    assert len(txts_in_sample) >= 1, "Expected at least one .txt file in the sampled folder"


def test_default_sampler_json_sampling(monkeypatch, tmp_path):
    """
    Test the sampling behavior when data_reducer is an instance of JsonReducer.
    This exercises:
    - inclusion of .json in included_extensions
    - json loading and reduction branch
    - construction of sample_used_file_names from sampled_files and copying of those files
    """
    import rdagent.scenarios.data_science.debug.data as data_mod

    # Create data folder and files
    data_root = tmp_path / "data"
    docs = data_root / "docs"
    data_root.mkdir()
    docs.mkdir()

    # JSON metadata file at root
    meta_json = data_root / "meta.json"
    meta_json.write_text(json.dumps({"meta": True}))

    # The sampled_files list will point to this doc file name
    doc_name = "doc1.txt"
    doc_path = docs / doc_name
    doc_path.write_text("document content")

    # Prepare a fake JsonReducer class and instance
    class FakeJsonReducer:
        def __init__(self, sampled_files):
            self.sampled_files = sampled_files
            self.min_num = 1
            self.min_frac = 0.5

        def reduce(self, data):
            # Return some processed representation (unused by code besides assignment)
            return {"reduced": True}

    fake_reducer = FakeJsonReducer(sampled_files=[doc_name])

    # Dummy data handler not used in JSON branch, but provide for completeness
    class DummyHandler:
        def load(self, path):
            return None

        def dump(self, df, target_path):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(str(df))

    dummy_handler = DummyHandler()

    # Monkeypatch module.JsonReducer to our FakeJsonReducer so isinstance check succeeds
    monkeypatch.setattr(data_mod, "JsonReducer", FakeJsonReducer)

    # Build sampler instance with JsonReducer instance
    sampler = _setup_sampler_instance(
        data_mod, tmp_path,
        data_reducer=fake_reducer, data_handler=dummy_handler,
        included_extensions={".csv", ".txt"}
    )

    # Monkeypatch helpers
    monkeypatch.setattr(data_mod, "count_files_in_folder", lambda files: {".txt": 0, ".json": 1})
    monkeypatch.setattr(data_mod, "copy_file", _make_copy_file(data_root, sampler.sample_folder))

    # Run the sample method
    sampler.sample()

    # The doc_path should have been copied into sample folder due to being listed in sampled_files
    expected_doc = sampler.sample_folder / doc_path.relative_to(data_root)
    assert expected_doc.exists(), f"Expected {expected_doc} to be present after sampling"

    # JSON file might not be copied (code doesn't copy json itself in that branch), but sample folder should contain at least the doc
    sampled_files = [p for p in sampler.sample_folder.rglob("*") if p.is_file()]
    assert any(p.name == doc_name for p in sampled_files), "sampled doc not found in sample folder"
