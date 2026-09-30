# file: browser_use/tools/service.py:1948-2030
# asked: {"lines": [1959, 1961, 1964, 1965, 1966, 1967, 1968, 1972, 1973, 1974, 1975, 1976, 1977, 1979, 1980, 1981, 1982, 1983, 1984, 1994, 1996, 1997, 1998, 1999, 2000, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2015, 2017, 2018, 2019, 2020, 2022, 2024, 2025, 2026, 2027, 2028, 2029], "branches": [[1964, 1965], [1964, 1972], [1965, 1966], [1965, 1972], [1967, 1965], [1967, 1968], [1973, 1974], [1973, 1979], [1975, 1976], [1975, 1979], [1976, 1975], [1976, 1977], [1999, 2000], [1999, 2002], [2003, 2004], [2003, 2022], [2004, 2005], [2004, 2017], [2006, 2007], [2006, 2011], [2008, 2006], [2008, 2009], [2011, 2012], [2011, 2015], [2017, 2018], [2017, 2022], [2019, 2017], [2019, 2020]]}
# gained: {"lines": [1959, 1961, 1964, 1965, 1966, 1967, 1968, 1972, 1973, 1974, 1975, 1976, 1977, 1979, 1980, 1981, 1982, 1983, 1984, 1994, 1996, 1997, 1998, 1999, 2000, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2015, 2017, 2018, 2019, 2020, 2022, 2024, 2025, 2026, 2027, 2028, 2029], "branches": [[1964, 1965], [1965, 1966], [1965, 1972], [1967, 1968], [1973, 1974], [1975, 1976], [1975, 1979], [1976, 1977], [1999, 2000], [1999, 2002], [2003, 2004], [2004, 2005], [2004, 2017], [2006, 2007], [2006, 2011], [2008, 2006], [2008, 2009], [2011, 2012], [2011, 2015], [2017, 2018], [2017, 2022], [2019, 2020]]}

import asyncio
import json
import pathlib
import logging
import pytest
from types import SimpleNamespace

from pydantic import BaseModel

from browser_use.tools.service import Tools as ToolsClass
from browser_use.agent.views import ActionResult

# Minimal fake registry to capture the registered action function
class FakeRegistry:
    def __init__(self):
        self.stored = None
        self.meta = None

    def action(self, *args, param_model=None, **kwargs):
        # store the metadata passed for potential inspection and return decorator
        def decorator(func):
            self.stored = func
            self.meta = {'args': args, 'param_model': param_model, 'kwargs': kwargs}
            return func
        return decorator

# Minimal fake filesystem
class FakeFileSystem:
    def __init__(self, base_dir: pathlib.Path, files: dict[str, str]):
        self._dir = base_dir
        self._files = files

    def display_file(self, name: str):
        # Return None or empty string for missing/empty files
        return self._files.get(name)

    def get_dir(self):
        return self._dir

# Minimal fake browser session
class FakeBrowserSession:
    def __init__(self, downloaded_files: list[str]):
        self.downloaded_files = downloaded_files

# A simple Pydantic model to use as StructuredOutputAction's generic parameter
class TestModel(BaseModel):
    field: str

@pytest.mark.asyncio
async def test_structured_output_includes_files_and_session_downloads(tmp_path):
    """
    Exercises the branch where output_model is not None:
    - params.files_to_display contains a file present in the filesystem
    - browser_session.downloaded_files contains an additional file not in attachments
    Verifies attachments, extracted_content, success and long_term_memory.
    """
    # Prepare fake self with registry
    fake_self = SimpleNamespace()
    fake_self.registry = FakeRegistry()

    # Call the method to register the action (output_model not None)
    # We pass a Pydantic BaseModel class as output_model to avoid schema generation errors
    ToolsClass._register_done_action(fake_self, output_model=TestModel, display_files_in_done_text=True)

    # Ensure the action got registered
    assert fake_self.registry.stored is not None
    done_func = fake_self.registry.stored

    # Prepare filesystem with one file 'a.txt'
    files = {'a.txt': 'hello world'}
    fs = FakeFileSystem(tmp_path, files)

    # Prepare browser session with a download that's not in attachments already
    session_downloads = [str(tmp_path / 'downloaded.bin')]
    browser_session = FakeBrowserSession(downloaded_files=session_downloads)

    # Prepare params: data.model_dump should return a dict via Pydantic BaseModel
    params = SimpleNamespace(data=TestModel(field='value'), success=True, files_to_display=['a.txt'])

    # Call the async done function
    result = await done_func(params, fs, browser_session)

    # Validate returned ActionResult-like object
    assert isinstance(result, ActionResult)
    assert result.is_done is True
    assert result.success is True

    # extracted_content is JSON dump of the dict returned by model_dump
    assert json.loads(result.extracted_content) == {'field': 'value'}

    # long_term_memory contains the success flag string
    assert 'Success Status: True' in result.long_term_memory

    # attachments should include the filesystem path for a.txt and the session download path
    expected_fs_path = str(tmp_path / 'a.txt')
    assert expected_fs_path in result.attachments
    assert session_downloads[0] in result.attachments

@pytest.mark.asyncio
async def test_done_action_with_display_files_in_done_text_and_long_text(tmp_path, caplog):
    """
    Exercises the branch where output_model is None and display_files_in_done_text is True.
    - First subcase: file exists -> should append file contents into the user_message and include attachment path.
    - Second subcase: file does not exist -> should log a warning and not add attachment content.
    Also exercises the long text path that appends "more characters" to memory.
    """
    caplog.set_level(logging.WARNING)

    # Create fake self with registry and display_files_in_done_text True
    fake_self = SimpleNamespace()
    fake_self.registry = FakeRegistry()
    fake_self.display_files_in_done_text = True

    # Register the action with output_model None to hit the DoneAction branch
    ToolsClass._register_done_action(fake_self, output_model=None)

    done_func = fake_self.registry.stored
    assert done_func is not None

    # Subcase 1: file exists and short text
    fs_files = {'report.txt': 'REPORT CONTENT'}
    fs = FakeFileSystem(tmp_path, fs_files)
    params = SimpleNamespace(text='Short message', success=False, files_to_display=['report.txt'])
    result = await done_func(params, fs)

    assert isinstance(result, ActionResult)
    assert result.success is False
    # extracted_content should include the attachments header and the file contents
    assert 'Attachments:' in result.extracted_content
    assert 'report.txt' in result.extracted_content
    assert 'REPORT CONTENT' in result.extracted_content
    # attachments should be converted to full paths
    assert result.attachments == [str(tmp_path / 'report.txt')]
    # memory should include the beginning of the text and not the "more characters" suffix
    assert 'more characters' not in result.long_term_memory

    # Subcase 2: file does not exist and long text triggers the "more characters" suffix
    fs2 = FakeFileSystem(tmp_path, {})  # no files
    long_text = 'x' * 150  # longer than len_max_memory (100)
    params2 = SimpleNamespace(text=long_text, success=True, files_to_display=['missing.txt'])
    # Ensure caplog picks up the warning
    result2 = await done_func(params2, fs2)
    # No attachments (missing file)
    assert result2.attachments == []
    # Memory should include the additional "more characters" note
    assert 'more characters' in result2.long_term_memory
    # Warning should have been emitted
    assert any('Agent wanted to display files but none were found' in rec.getMessage() for rec in caplog.records)

@pytest.mark.asyncio
async def test_done_action_with_display_files_not_in_done_text(tmp_path):
    """
    Exercises the branch where output_model is None and display_files_in_done_text is False.
    Ensures attachments are included but not appended into the user message.
    """
    fake_self = SimpleNamespace()
    fake_self.registry = FakeRegistry()
    fake_self.display_files_in_done_text = False

    ToolsClass._register_done_action(fake_self, output_model=None)
    done_func = fake_self.registry.stored
    assert done_func is not None

    # File exists
    fs = FakeFileSystem(tmp_path, {'only.txt': 'content'})
    params = SimpleNamespace(text='Message', success=True, files_to_display=['only.txt'])
    result = await done_func(params, fs)

    # The extracted_content should NOT include the 'Attachments:' insertion since display_files_in_done_text is False
    assert 'Attachments:' not in result.extracted_content
    # But attachments should still include the file (converted to dir path)
    assert result.attachments == [str(tmp_path / 'only.txt')]
    assert result.is_done is True
