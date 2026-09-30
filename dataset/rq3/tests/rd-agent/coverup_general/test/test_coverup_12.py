# file: rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py:744-873
# asked: {"lines": [766, 767, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 801, 802, 803, 805, 806, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 822, 823, 825, 826, 827, 828, 829, 830, 832, 833, 834, 836, 840, 841, 842, 845, 848, 849, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 862, 863, 864, 865, 867, 869, 870, 871, 872, 873], "branches": [[771, 772], [771, 781], [773, 774], [773, 775], [775, 776], [775, 781], [776, 775], [776, 777], [781, 782], [781, 822], [782, 783], [782, 840], [783, 784], [783, 785], [785, 786], [785, 788], [786, 787], [786, 788], [788, 782], [788, 789], [789, 790], [789, 791], [801, 802], [801, 805], [828, 829], [828, 832], [840, 841], [840, 845], [855, 856], [855, 857], [857, 858], [857, 860], [872, 0], [872, 873]]}
# gained: {"lines": [766, 767, 770, 771, 772, 773, 775, 776, 777, 778, 779, 781, 782, 783, 785, 786, 788, 789, 791, 792, 793, 794, 795, 796, 797, 798, 799, 801, 802, 803, 805, 806, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 822, 823, 825, 826, 827, 828, 832, 833, 834, 836, 840, 841, 842, 845, 848, 849, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 862, 863, 864, 865, 867, 869, 870, 871, 872, 873], "branches": [[771, 772], [771, 781], [773, 775], [775, 776], [775, 781], [776, 777], [781, 782], [781, 822], [782, 783], [782, 840], [783, 785], [785, 786], [786, 788], [788, 782], [788, 789], [789, 791], [801, 802], [801, 805], [828, 832], [840, 841], [840, 845], [855, 856], [855, 857], [857, 858], [872, 0], [872, 873]]}

import importlib
import json
import pickle
from types import SimpleNamespace
from pathlib import Path
import shutil

import pytest

MODULE_PATH = "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"


@pytest.fixture
def submit_module():
    return importlib.import_module(MODULE_PATH)


def test_yaml_debug_then_non_debug_branch_removes_log_and_writes_result(tmp_path, monkeypatch, submit_module):
    # Setup a trace_root path that contains 'yaml' in its string so the YAML branch is exercised
    trace_root_dir = tmp_path / "some_yaml_root"
    trace_root_dir.mkdir()
    experiment_name = "exp_yaml"
    yaml_path = trace_root_dir / f"{experiment_name}.yaml"

    # Create a fake job entry that matches competition
    job_info = [
        {
            "results_dir": "resdir",
            "submit_args": {"env": {"DS_COMPETITION": "comp1", "RD_RES_NAME": "resname"}},
        }
    ]
    # safe_load accepts JSON; write JSON representation
    yaml_path.write_text(json.dumps(job_info))

    # Create 'log' directory with a child folder and also create 'log/log' to be removed later
    log_root = Path("log")
    # Ensure starting from clean state
    if log_root.exists():
        shutil.rmtree(log_root)
    # Create log/log which should be removed by the function
    (log_root / "log").mkdir(parents=True)
    # Create another directory that will be chosen by the generator in the function
    (log_root / "mylog").mkdir()

    # Prepare a fake FileStorage class
    class FakeMsg:
        def __init__(self, content):
            self.content = content

    class FakeFileStorage:
        def __init__(self, path):
            self._path = Path(path)

        def iter_msg(self, tag=None):
            return [FakeMsg({"fake": "trace"})]

    monkeypatch.setattr(submit_module, "FileStorage", FakeFileStorage)

    # Patch extract_tar to record the call
    called = {}

    def fake_extract_tar(path):
        called["tar"] = path

    monkeypatch.setattr(submit_module, "extract_tar", fake_extract_tar)

    # Patch multiprocessing_wrapper to return a predictable hit_list
    def fake_multiprocessing_wrapper(tasks, n=1):
        return [("compX", 1, {"medal": "gold"})]

    monkeypatch.setattr(submit_module, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    # Run function
    trace_root_str = str(trace_root_dir)  # contains 'yaml'
    monkeypatch.delenv("DS_COMPETITION", raising=False)
    submit_module.select_on_existing_trace("selector_yaml", trace_root_str, experiment=experiment_name, competition="comp1", debug=True)

    # Assertions:
    expected_tar = Path("/mnt/output") / "resdir" / "resname"
    assert "tar" in called
    assert Path(called["tar"]) == expected_tar

    result_file = Path(f"result_selector_yaml.json")
    assert result_file.exists()
    data = json.loads(result_file.read_text())
    assert data["summary"]["hit"] == 1
    assert data["summary"]["total"] == 1
    # log/log should have been removed
    assert not (log_root / "log").exists()

    # Cleanup
    result_file.unlink()
    if log_root.exists():
        shutil.rmtree(log_root)


def test_debug_branch_missing_and_empty_loops(tmp_path, monkeypatch, submit_module):
    # Prepare trace_root without the substring 'yaml' so we do not hit the YAML branch
    trace_root = tmp_path / "traces_no"
    trace_root.mkdir()
    exp_folder = trace_root / "expA"
    exp_folder.mkdir()

    # Use SimpleNamespace for picklable objects
    trace_obj = SimpleNamespace(scen=SimpleNamespace(competition="compA"))
    pkl_path = exp_folder / "compA_trace.pkl"
    with pkl_path.open("wb") as f:
        pickle.dump(trace_obj, f)

    # Case 1: missing loops file -> FileNotFoundError branch should be triggered and function returns early
    def fail_mp(tasks, n=1):
        pytest.skip("multiprocessing_wrapper should not be called in this test")

    monkeypatch.setattr(submit_module, "multiprocessing_wrapper", fail_mp)

    submit_module.select_on_existing_trace("selector_missing", str(trace_root), experiment="expA", debug=True)

    assert not Path("result_selector_missing.json").exists()

    # Case 2: create loops file but with empty medal_loops to trigger "No Medal loops defined" branch
    loops_file = exp_folder / "compA_loops.json"
    loops_file.write_text(json.dumps({"medal_loops": []}))

    submit_module.select_on_existing_trace("selector_nomedal", str(trace_root), experiment="expA", debug=True)

    assert not Path("result_selector_nomedal.json").exists()


def test_debug_branch_with_medal_appends_tasks_and_writes_result(tmp_path, monkeypatch, submit_module):
    # Prepare trace_root without 'yaml' and with loops containing medal_loops to exercise tasks.append path
    trace_root = tmp_path / "traces_with_medal"
    trace_root.mkdir()
    exp_folder = trace_root / "expB"
    exp_folder.mkdir()

    # Create a pickled trace object using SimpleNamespace
    trace_obj = SimpleNamespace(scen=SimpleNamespace(competition="compB"))
    pkl_path = exp_folder / "compB_trace.pkl"
    with pkl_path.open("wb") as f:
        pickle.dump(trace_obj, f)

    # Create loops file with medal_loops present
    loops_file = exp_folder / "compB_loops.json"
    loops_file.write_text(json.dumps({"medal_loops": [{"loop": 1}], "other": "info"}))

    # Patch multiprocessing_wrapper to validate tasks structure and return a hit_list
    def fake_multiprocessing_wrapper(tasks, n=1):
        assert isinstance(tasks, list)
        func, args = tasks[0]
        assert callable(func)
        assert args[0] == "selector_debug"
        assert isinstance(args[5], dict) and args[5].get("medal_loops")
        assert args[6] == "expB"
        return [("compB", 0, {})]

    monkeypatch.setattr(submit_module, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    submit_module.select_on_existing_trace("selector_debug", str(trace_root), experiment="expB", debug=True)

    result_file = Path("result_selector_debug.json")
    assert result_file.exists()
    data = json.loads(result_file.read_text())
    assert data["summary"]["hit"] == 0
    assert data["summary"]["total"] == 1
    # Cleanup
    result_file.unlink()
