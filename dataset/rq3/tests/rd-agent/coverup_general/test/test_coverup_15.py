# file: rdagent/scenarios/kaggle/kaggle_crawler.py:110-200
# asked: {"lines": [111, 112, 113, 114, 115, 117, 118, 119, 120, 121, 122, 123, 124, 127, 128, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 144, 145, 146, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 160, 161, 162, 163, 168, 169, 170, 171, 172, 173, 175, 176, 178, 179, 180, 181, 182, 183, 187, 188, 189, 192, 193, 194, 195, 196, 199, 200], "branches": [[112, 113], [112, 178], [117, 118], [117, 127], [127, 128], [127, 199], [136, 137], [136, 148], [138, 139], [138, 144], [148, 149], [148, 168], [149, 150], [149, 152], [154, 155], [154, 160], [168, 169], [168, 199], [172, 173], [172, 175], [179, 180], [179, 199], [193, 194], [193, 199], [195, 196], [195, 199], [199, 0], [199, 200]]}
# gained: {"lines": [111, 112, 113, 114, 115, 117, 118, 119, 120, 121, 122, 123, 124, 127, 128, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 144, 145, 146, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 160, 161, 162, 163, 168, 169, 170, 171, 172, 173, 175, 176, 178, 179, 180, 181, 182, 183, 187, 188, 189, 192, 193, 194, 195, 196, 199, 200], "branches": [[112, 113], [112, 178], [117, 118], [127, 128], [136, 137], [136, 148], [138, 139], [138, 144], [148, 149], [148, 168], [149, 150], [149, 152], [154, 155], [154, 160], [168, 169], [172, 173], [172, 175], [179, 180], [193, 194], [195, 196], [195, 199], [199, 200]]}

import io
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

import rdagent.scenarios.kaggle.kaggle_crawler as kc


class DummySettings:
    def __init__(self, local_data_path: str, if_using_mle_data: bool):
        self.local_data_path = local_data_path
        self.if_using_mle_data = if_using_mle_data


def make_zip(path: Path, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def make_tar(path: Path, members, gz=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w:gz" if gz else "w"
    with tarfile.open(path, mode) as tf:
        for name, data in members.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))


def test_if_using_mle_data_handles_zip_and_tar_and_labels_and_create_debug(tmp_path, monkeypatch):
    # We will provide a fake MLEBDockerEnv that, when mlebench prepare is requested,
    # creates zip_files/<competition>/prepared/public with test zips/tars/labels,
    # and when cp -r is requested it copies them to the competition local folder.
    mleb_instances = []

    class FakeMLEBDockerEnv:
        def __init__(self):
            self.prepared = False
            self.commands = []
            mleb_instances.append(self)

        def prepare(self):
            self.prepared = True

        def check_output(self, cmd, local_path=None, running_extra_volume=None):
            self.commands.append((cmd, local_path, running_extra_volume))
            # If mlebench prepare, create the source prepared files
            if isinstance(cmd, str) and cmd.startswith("mlebench prepare"):
                # parse competition name from command string: -c <competition>
                parts = cmd.split()
                comp = None
                if "-c" in parts:
                    idx = parts.index("-c")
                    if idx + 1 < len(parts):
                        comp = parts[idx + 1]
                # fallback: look for '--data-dir' not needed here
                if comp is None:
                    raise RuntimeError("Could not parse competition from mlebench command")
                src = Path(local_path) / "zip_files" / comp / "prepared" / "public"
                # create some files
                # single-member zip
                make_zip(src / "single.zip", {"only.txt": b"hello"})
                # multi-member zip
                make_zip(src / "multi.zip", {"a.txt": b"1", "b.txt": b"2"})
                # invalid tar (not a tar)
                src.mkdir(parents=True, exist_ok=True)
                (src / "invalid.tar").write_text("not a tar")
                # single-member gz tar
                make_tar(src / "single.tar.gz", {"only.txt": b"h"}, gz=True)
                # multi tar
                make_tar(src / "multi.tar", {"a.txt": b"1", "b.txt": b"2"}, gz=False)
                # labels.csv to be copied into competition folder later
                (src / "labels.csv").write_text("labeldata")
                return "prepared"
            # If cp -r command, simulate copying from zip_files/.../prepared/public to ./{competition}
            if isinstance(cmd, str) and cmd.startswith("cp -r"):
                # cmd like: cp -r ./zip_files/{competition}/prepared/public/* ./{competition}
                # find './zip_files' in local_path
                # extract competition from command by finding './zip_files/' and next token until '/prepared'
                s = cmd
                marker = "./zip_files/"
                if marker in s and "/prepared" in s:
                    start = s.index(marker) + len(marker)
                    end = s.index("/prepared", start)
                    comp = s[start:end]
                else:
                    raise RuntimeError("Could not parse cp command")
                src = Path(local_path) / "zip_files" / comp / "prepared" / "public"
                dest = Path(local_path) / comp
                dest.mkdir(parents=True, exist_ok=True)
                # copy files and directories
                for it in src.iterdir():
                    if it.is_dir():
                        shutil.copytree(it, dest / it.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(it, dest / it.name)
                return "copied"
            # For other commands (unzip/tar) we simply simulate success
            return "ok"

    monkeypatch.setattr(kc, "MLEBDockerEnv", FakeMLEBDockerEnv)

    called_create_debug = {"called": False, "args": None}

    def fake_create_debug_data(competition, dataset_path):
        called_create_debug["called"] = True
        called_create_debug["args"] = (competition, dataset_path)

    monkeypatch.setattr(kc, "create_debug_data", fake_create_debug_data)

    settings = DummySettings(local_data_path=str(tmp_path / "data"), if_using_mle_data=True)
    competition = "new-york-city-taxi-fare-prediction"

    # Ensure zip_files/competition does NOT exist so mlebench prepare branch runs
    src_zip_comp = Path(settings.local_data_path) / "zip_files" / competition
    if src_zip_comp.exists():
        shutil.rmtree(src_zip_comp)

    # Ensure competition_local_path does not exist so the branch creating it and processing runs
    competition_local_path = Path(settings.local_data_path) / competition
    if competition_local_path.exists():
        shutil.rmtree(competition_local_path)

    # Now call the function; our FakeMLEBDockerEnv will create prepared files on mlebench prepare,
    # and will copy them during cp -r
    kc.download_data(competition, settings, enable_create_debug_data=True)

    # Assertions:
    # At least one MLEB env was prepared
    assert any(inst.prepared for inst in mleb_instances), "MLEB prepare was not called on any instance"
    # There should be commands that include mlebench prepare and cp -r
    merged_cmds = " ".join(cmd for inst in mleb_instances for cmd, *_ in inst.commands if isinstance(cmd, str))
    assert "mlebench prepare" in merged_cmds
    assert "cp -r ./zip_files" in merged_cmds
    # train.csv should be created and match labels content (labels copied to train.csv)
    train = competition_local_path / "train.csv"
    assert train.exists()
    assert train.read_text() == "labeldata"
    # create_debug_data should have been called with competition and dataset path
    assert called_create_debug["called"] is True
    assert called_create_debug["args"] == (competition, settings.local_data_path)


def test_if_using_mle_data_labels_missing_raises(tmp_path, monkeypatch):
    # Similar fake env but do not create labels so the code raises FileNotFoundError
    class FakeMLEBNoLabels:
        def __init__(self):
            self.prepared = False

        def prepare(self):
            self.prepared = True

        def check_output(self, cmd, local_path=None, running_extra_volume=None):
            # On mlebench prepare create a prepared/public but without labels.csv
            if isinstance(cmd, str) and cmd.startswith("mlebench prepare"):
                parts = cmd.split()
                comp = None
                if "-c" in parts:
                    idx = parts.index("-c")
                    if idx + 1 < len(parts):
                        comp = parts[idx + 1]
                src = Path(local_path) / "zip_files" / comp / "prepared" / "public"
                src.mkdir(parents=True, exist_ok=True)
                make_zip(src / "single.zip", {"only.txt": b"1"})
                return "prepared"
            # For cp -r simulate copying prepared files
            if isinstance(cmd, str) and cmd.startswith("cp -r"):
                parts = cmd
                s = cmd
                marker = "./zip_files/"
                if marker in s and "/prepared" in s:
                    start = s.index(marker) + len(marker)
                    end = s.index("/prepared", start)
                    comp = s[start:end]
                src = Path(local_path) / "zip_files" / comp / "prepared" / "public"
                dest = Path(local_path) / comp
                dest.mkdir(parents=True, exist_ok=True)
                for it in src.iterdir():
                    if it.is_dir():
                        shutil.copytree(it, dest / it.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(it, dest / it.name)
                return "copied"
            return "ok"

    monkeypatch.setattr(kc, "MLEBDockerEnv", FakeMLEBNoLabels)

    called_create_debug = {"called": False}

    def fake_create_debug_data(competition, dataset_path):
        called_create_debug["called"] = True

    monkeypatch.setattr(kc, "create_debug_data", fake_create_debug_data)

    settings = DummySettings(local_data_path=str(tmp_path / "data2"), if_using_mle_data=True)
    competition = "new-york-city-taxi-fare-prediction"

    # Ensure no prepared files exist initially
    src_zip_comp = Path(settings.local_data_path) / "zip_files" / competition
    if src_zip_comp.exists():
        shutil.rmtree(src_zip_comp)
    # Ensure competition folder does not exist so branch runs
    comp_local = Path(settings.local_data_path) / competition
    if comp_local.exists():
        shutil.rmtree(comp_local)

    with pytest.raises(FileNotFoundError):
        kc.download_data(competition, settings, enable_create_debug_data=True)

    # create_debug_data should not have been called due to exception
    assert not called_create_debug["called"]


def test_not_using_mle_data_calls_subprocess_and_unzip_and_create_debug(tmp_path, monkeypatch):
    # Patch subprocess.run to simulate successful kaggle download
    calls = {"subproc": 0, "unzip_calls": [], "create_debug": 0}

    def fake_run(cmd, check, stderr, stdout):
        calls["subproc"] += 1
        # Simulate creation of the zip file in zipfile_path
        zipfile_path = Path(str(tmp_path / "data3")) / "zip_files"
        zipfile_path.mkdir(parents=True, exist_ok=True)
        # write an empty zip representing competition.zip
        # Name should match competition.zip; we'll use 'somecomp.zip'
        (zipfile_path / "somecomp.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty zip footer
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Patch unzip_data to simulate unzipping and to create a nested zip to trigger second loop
    def fake_unzip(unzip_file_path, unzip_target_path):
        # Accept both Path and str
        path_obj = Path(unzip_file_path)
        target = Path(unzip_target_path)
        target.mkdir(parents=True, exist_ok=True)
        # create a sub zip to be found by rglob("*.zip")
        make_zip(target / "inner.zip", {"in.txt": b"data"})
        calls["unzip_calls"].append(str(path_obj.name))
        return True

    monkeypatch.setattr(kc, "unzip_data", fake_unzip)

    def fake_create_debug(competition, dataset_path):
        calls["create_debug"] += 1

    monkeypatch.setattr(kc, "create_debug_data", fake_create_debug)

    settings = DummySettings(local_data_path=str(tmp_path / "data3"), if_using_mle_data=False)
    competition = "somecomp"

    # Ensure zip file does not exist initially to trigger subprocess.run path
    zip_comp = Path(settings.local_data_path) / "zip_files" / f"{competition}.zip"
    if zip_comp.exists():
        zip_comp.unlink()

    # Run
    kc.download_data(competition, settings, enable_create_debug_data=True)

    # Assertions
    assert calls["subproc"] == 1
    # unzip_data should have been called at least once (initial unzip) and then for nested zip
    assert len(calls["unzip_calls"]) >= 1
    # create_debug_data should have been called
    assert calls["create_debug"] == 1


def test_not_using_mle_data_subprocess_failure_raises_kaggleerror(tmp_path, monkeypatch):
    # Simulate subprocess.run raising CalledProcessError
    def fake_run_fail(cmd, check, stderr, stdout):
        e = subprocess.CalledProcessError(1, cmd)
        # Attach attributes expected by download_data logging
        e.stderr = b"err"
        e.stdout = b"out"
        raise e

    monkeypatch.setattr(subprocess, "run", fake_run_fail)
    settings = DummySettings(local_data_path=str(tmp_path / "data4"), if_using_mle_data=False)
    competition = "failcomp"
    # Ensure zip does not exist
    zip_comp = Path(settings.local_data_path) / "zip_files" / f"{competition}.zip"
    if zip_comp.exists():
        zip_comp.unlink()

    with pytest.raises(kc.KaggleError):
        kc.download_data(competition, settings, enable_create_debug_data=False)
