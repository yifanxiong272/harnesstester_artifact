import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.batch_instances')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Verify that when shuffle=True the function sorts then shuffles deterministically."""
        # lightweight dummy objects that provide the attribute access used by the function
        class PS:
            def __init__(self, id_):
                self.id = id_

        class Inst:
            def __init__(self, id_):
                self.problem_statement = PS(id_)

        # start with a reverse-ordered list so sorting changes it first
        original_ids = ["e", "d", "c", "b", "a"]
        instances = [Inst(i) for i in original_ids]

        # call with shuffle=True to exercise the target lines (sorting + random.seed + shuffle)
        result = _filter_batch_items(instances, filter_=".*", shuffle=True)

        result_ids = [inst.problem_statement.id for inst in result]

        # same elements must be present
        self.assertCountEqual(result_ids, original_ids)
        # length unchanged
        self.assertEqual(len(result_ids), len(original_ids))
        # after sorting the ids would be ascending; shuffling should change that order
        self.assertNotEqual(result_ids, sorted(original_ids))
