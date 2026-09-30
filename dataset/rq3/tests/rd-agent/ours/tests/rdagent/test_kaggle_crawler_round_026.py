import subprocess
import tarfile
import zipfile
from pathlib import Path
import io
import os
import pytest

from rdagent.scenarios.kaggle import kaggle_crawler as kc
from rdagent.core.exception import KaggleError


class DummySettings:
    def __init__(self, local_data_path: str, if_using_mle_data: bool):
        self.local_data_path = local_data_path
        self.if_using_mle_data = if_using_mle_data


class FakeMLEBDockerEnv:
    def __init__(self):
        self.prepared = False
        self.check_calls = []

    def prepare(self):
        # record that prepare was called
        self.prepared = True

    def check_output(self, cmd, local_path=None, running_extra_volume=None):
        # record the command for assertions
        self.check_calls.append((cmd, local_path))
        # simulate the behavior of the cp -r step by creating files expected
        # by later parts of the logic (zip and tar files and labels.csv).
        if isinstance(cmd, str) and cmd.startswith("cp -r") and local_path is not None:
            # extract competition name from the cp command
            # cp -r ./zip_files/{competition}/prepared/public/* ./{competition}
            try:
                # primitive parse to get {competition}
                inside = cmd.split("./zip_files/")[1]
                competition = inside.split("/")[0]
            except Exception:
                competition = "competition"
            comp_dir = Path(local_path) / competition
            comp_dir.mkdir(parents=True, exist_ok=True)
            # create a file to put in the zip
            file_for_zip = comp_dir / "sample.txt"
            file_for_zip.write_text("hello")
            # create a .zip archive with a single member
            zip_path = comp_dir / "single_file.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("only.txt", "content")
            # create a .tar archive with a single member
            tar_path = comp_dir / "single_file.tar"
            with tarfile.open(tar_path, "w") as tf:
                # write a real file and add it
                member_file = comp_dir / "tf_member.txt"
                member_file.write_text("tardata")
                tf.add(str(member_file), arcname="tf_member.txt")
            # create labels.csv to trigger the labels->train copy branch later
            (comp_dir / "labels.csv").write_text("a,b,c\n")
        return None


def test_download_data_mle_with_labels_round_026(tmp_path, monkeypatch):
    # Arrange
    competition = "new-york-city-taxi-fare-prediction"
    local_path = str(tmp_path)
    settings = DummySettings(local_data_path=local_path, if_using_mle_data=True)

    fake_mleb = FakeMLEBDockerEnv()

    # Patch MLEBDockerEnv used in the module to our fake
    monkeypatch.setattr(kc, "MLEBDockerEnv", lambda: fake_mleb)

    # Patch shutil.copy to record calls
    copy_calls = []

    def fake_copy(src, dst):
        copy_calls.append((src, dst))
        # actually create the dst file to mimic real copy
        Path(dst).write_text(Path(src).read_text())

    monkeypatch.setattr(kc, "shutil", kc.shutil)
    monkeypatch.setattr(kc.shutil, "copy", fake_copy)

    # Patch create_debug_data to record invocation and avoid external behavior
    create_calls = []

    def fake_create_debug_data(comp, dataset_path=None):
        create_calls.append((comp, dataset_path))

    monkeypatch.setattr(kc, "create_debug_data", fake_create_debug_data)

    # Ensure no sample dir exists yet, to trigger sample data creation
    sample_dir = Path(local_path) / "sample" / competition
    if sample_dir.exists():
        # Clean up in case
        for p in sample_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        sample_dir.rmdir()

    # Act
    # Should not raise
    kc.download_data(competition=competition, settings=settings, enable_create_debug_data=True)

    # Assert
    # MLEB prepare should have been called (prepare flips prepared flag)
    assert fake_mleb.prepared is True
    # cp -r and unzip/tar operations should have been recorded in check_calls
    cmds = [c for c, _ in fake_mleb.check_calls]
    assert any("mlebench prepare" in str(cmd) for cmd in cmds) or len(cmds) >= 1
    # We expect cp -r to have been called (simulated)
    assert any("cp -r" in str(cmd) for cmd in cmds)
    # shutil.copy should have been called to copy labels.csv -> train.csv
    assert any("labels.csv" in str(src) for src, dst in copy_calls)
    # create_debug_data must be called once to generate sample data
    assert create_calls == [(competition, local_path)]


def test_download_data_kaggle_download_fail_round_026(tmp_path, monkeypatch):
    # Arrange
    competition = "some-competition"
    local_path = str(tmp_path)
    settings = DummySettings(local_data_path=local_path, if_using_mle_data=False)

    # Ensure the zip does not exist to force a download attempt
    zipfile_dir = Path(local_path) / "zip_files"
    (zipfile_dir).mkdir(parents=True, exist_ok=True)
    target_zip = zipfile_dir / f"{competition}.zip"
    if target_zip.exists():
        target_zip.unlink()

    # Patch subprocess.run to simulate a failed kaggle CLI
    def fake_run(cmd, check, stderr, stdout):
        # raise as subprocess would
        e = subprocess.CalledProcessError(1, cmd)
        e.stderr = b"err"
        e.stdout = b"out"
        raise e

    monkeypatch.setattr(kc, "subprocess", kc.subprocess)
    monkeypatch.setattr(kc.subprocess, "run", fake_run)

    # Act & Assert: should raise KaggleError wrapping the CalledProcessError
    with pytest.raises(KaggleError) as excinfo:
        kc.download_data(competition=competition, settings=settings, enable_create_debug_data=False)

    # The message should include 'Download failed' and show stdout/stderr info
    assert "Download failed" in str(excinfo.value)
