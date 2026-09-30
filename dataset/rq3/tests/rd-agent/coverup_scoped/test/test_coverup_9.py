# file: rdagent/scenarios/kaggle/kaggle_crawler.py:110-200
# asked: {"lines": [111, 112, 113, 114, 115, 117, 118, 119, 120, 121, 122, 123, 124, 127, 128, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 144, 145, 146, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 160, 161, 162, 163, 168, 169, 170, 171, 172, 173, 175, 176, 178, 179, 180, 181, 182, 183, 187, 188, 189, 192, 193, 194, 195, 196, 199, 200], "branches": [[112, 113], [112, 178], [117, 118], [117, 127], [127, 128], [127, 199], [136, 137], [136, 148], [138, 139], [138, 144], [148, 149], [148, 168], [149, 150], [149, 152], [154, 155], [154, 160], [168, 169], [168, 199], [172, 173], [172, 175], [179, 180], [179, 199], [193, 194], [193, 199], [195, 196], [195, 199], [199, 0], [199, 200]]}
# gained: {"lines": [111, 112, 113, 114, 115, 117, 127, 128, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 144, 145, 146, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 160, 161, 162, 163, 168, 169, 170, 171, 172, 173, 175, 176, 178, 179, 180, 181, 182, 183, 187, 188, 189, 192, 193, 194, 195, 199, 200], "branches": [[112, 113], [112, 178], [117, 127], [127, 128], [136, 137], [136, 148], [138, 139], [138, 144], [148, 149], [148, 168], [149, 150], [149, 152], [154, 155], [154, 160], [168, 169], [172, 173], [172, 175], [179, 180], [193, 194], [195, 199], [199, 200]]}

import subprocess
import tarfile
import zipfile
from pathlib import Path
import shutil
import io

import pytest
import importlib

module = importlib.import_module("rdagent.scenarios.kaggle.kaggle_crawler")
download_data = module.download_data
KaggleError = module.KaggleError

class FakeMLEB:
    def __init__(self):
        self.prepared = False
        self.commands = []

    def prepare(self):
        self.prepared = True

    def check_output(self, cmd, local_path=None, running_extra_volume=None):
        # record commands
        self.commands.append((cmd, local_path, running_extra_volume))
        cmd = str(cmd)
        # simulate the cp -r behavior to copy prepared/public contents into competition folder
        if cmd.startswith("cp -r"):
            # expected pattern: cp -r ./zip_files/{competition}/prepared/public/* ./{competition}
            if local_path is None:
                return ""
            parts = cmd.split()
            try:
                src_part = parts[2]  # ./zip_files/.../prepared/public/*
                src_part = src_part.replace("./", "")
                src_dir = Path(local_path) / Path(src_part).parent
                dest_part = parts[3]  # ./{competition}
                dest_part = dest_part.replace("./", "")
                dest_dir = Path(local_path) / Path(dest_part)
                dest_dir.mkdir(parents=True, exist_ok=True)
                if src_dir.exists():
                    for p in src_dir.iterdir():
                        if p.is_dir():
                            target = dest_dir / p.name
                            if target.exists():
                                shutil.rmtree(target)
                            shutil.copytree(p, target)
                        else:
                            shutil.copy2(p, dest_dir / p.name)
            except Exception:
                pass
        return ""

@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    # Patch MLEBDockerEnv in the module to our fake
    monkeypatch.setattr(module, "MLEBDockerEnv", lambda: FakeMLEB())
    # patch create_debug_data to track calls
    calls = {"create_debug": []}
    def fake_create_debug_data(competition, dataset_path=None):
        calls["create_debug"].append((competition, dataset_path))
    monkeypatch.setattr(module, "create_debug_data", fake_create_debug_data)
    return calls

def make_zip(path: Path, name: str, members):
    zpath = path / name
    zpath.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "w") as zf:
        for member_name, content in members.items():
            zf.writestr(member_name, content)
    return zpath

def make_tar(path: Path, name: str, members, gz=False):
    tpath = path / name
    tpath.parent.mkdir(parents=True, exist_ok=True)
    mode = "w:gz" if gz else "w"
    with tarfile.open(tpath, mode) as tf:
        for mname, content in members.items():
            data = content.encode()
            info = tarfile.TarInfo(name=mname)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return tpath

def test_mle_processing_with_labels_copy(tmp_path, patch_env):
    # Setup: create zip_files/competition/prepared/public with zip and tar files and labels.csv
    competition = "new-york-city-taxi-fare-prediction"
    local = tmp_path
    zipfile_path = local / "zip_files" / competition / "prepared" / "public"
    zipfile_path.mkdir(parents=True, exist_ok=True)

    # create a zip file with one member
    make_zip(zipfile_path, "single.zip", {"only.txt": "content1"})
    # create a zip file with multiple members
    make_zip(zipfile_path, "multi.zip", {"a.txt": "1", "b.txt": "2"})
    # create an invalid .tar file (not a tar)
    invalid_tar = zipfile_path / "notatar.tar"
    invalid_tar.write_text("this is not a tar")

    # create a plain tar with one member
    make_tar(zipfile_path, "one.tar", {"file.txt": "hello"}, gz=False)
    # create a gz tar with multiple members
    make_tar(zipfile_path, "many.tar.gz", {"x.txt": "x", "y.txt": "y"}, gz=True)

    # create labels.csv so it will be copied to train.csv
    labels_content = "id,value\n1,100\n"
    (zipfile_path / "labels.csv").write_text(labels_content)

    settings = type("S", (), {"local_data_path": str(local), "if_using_mle_data": True})

    # Run
    download_data(competition, settings, enable_create_debug_data=True)

    # Assertions:
    cpath = local / competition
    assert cpath.exists()
    train = cpath / "train.csv"
    assert train.exists()
    # Since FakeMLEB.copy behavior copied labels.csv into competition folder root
    assert train.read_text() == labels_content
    # create_debug_data should have been called (sample path not existing)
    assert patch_env["create_debug"], "create_debug_data should have been called"

def test_mle_processing_missing_labels_raises(tmp_path):
    # Setup similar to previous but without labels.csv to trigger FileNotFoundError
    competition = "new-york-city-taxi-fare-prediction"
    local = tmp_path
    zipfile_path = local / "zip_files" / competition / "prepared" / "public"
    zipfile_path.mkdir(parents=True, exist_ok=True)

    # minimal zip so copy happens
    make_zip(zipfile_path, "single.zip", {"only.txt": "content1"})
    # no labels.csv present

    settings = type("S", (), {"local_data_path": str(local), "if_using_mle_data": True})

    with pytest.raises(FileNotFoundError):
        download_data(competition, settings, enable_create_debug_data=False)

def test_non_mle_subprocess_failure_raises(tmp_path, monkeypatch):
    competition = "some-competition"
    local = tmp_path
    settings = type("S", (), {"local_data_path": str(local), "if_using_mle_data": False})

    # Ensure no zip exists so subprocess.run will be invoked
    def fake_run(*args, **kwargs):
        # Construct CalledProcessError with output and stderr keywords supported across versions
        raise subprocess.CalledProcessError(1, args[0], output=b"out", stderr=b"err")
    # Patch the subprocess.run used inside the module
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    with pytest.raises(KaggleError):
        download_data(competition, settings, enable_create_debug_data=False)

def test_non_mle_success_runs_unzip_and_creates_debug(tmp_path, monkeypatch, patch_env):
    competition = "other-competition"
    local = tmp_path
    settings = type("S", (), {"local_data_path": str(local), "if_using_mle_data": False})

    # Do NOT create the zip so the code will call subprocess.run
    # Patch subprocess.run to be a no-op (simulate success)
    def fake_run_ok(*args, **kwargs):
        class C:
            returncode = 0
        return C()
    monkeypatch.setattr(module.subprocess, "run", fake_run_ok)

    # Patch unzip_data to record calls
    called = {"unzip": []}
    def fake_unzip(unzip_file_path, unzip_target_path):
        called["unzip"].append((unzip_file_path, unzip_target_path))
        Path(unzip_target_path).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, "unzip_data", fake_unzip)

    # Run
    download_data(competition, settings, enable_create_debug_data=True)

    # Assertions
    assert called["unzip"], "unzip_data should have been called"
    assert patch_env["create_debug"], "create_debug_data should have been called"
