"""Keep user-facing documentation links and paragraph layout consistent."""

from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    ROOT / name for name in (
        "README.md", "SETUP.md", "dataset/README.md",
        "resources/inputs/README.md", "resources/benchmark/README.md",
        "resources/subjects/README.md",
        "src/augment/README.md", "src/probe/README.md",
        "src/llm_dependent/README.md", "src/collect_coverage/README.md",
    )
]


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_local_links_resolve(document):
    for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
        link = urlsplit(target)
        if link.scheme or link.netloc:
            continue
        path = (document.parent / unquote(link.path)).resolve() if link.path else document
        assert path.exists(), (document, target)
        if link.fragment and path.suffix == ".md":
            headings = re.findall(r"^#{1,6}\s+(.+)$", path.read_text(), flags=re.MULTILINE)
            anchors = {re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-") for heading in headings}
            assert unquote(link.fragment) in anchors, (document, target)


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_paragraphs_use_one_physical_line(document):
    in_code = False
    previous_prose = False
    for number, line in enumerate(document.read_text().splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
        prose = bool(line.strip()) and not in_code and not re.match(r"^\s*(?:```|#|\||[-*+] |\d+\. )", line)
        assert not (previous_prose and prose), (document, number)
        previous_prose = prose


def test_dataset_readme_uses_one_directory_list():
    lines = (ROOT / "dataset/README.md").read_text().splitlines()
    assert lines[0] == "# Study Results"
    assert all(re.match(r"^ *- ", line) for line in lines[1:] if line.strip())


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_commands_use_repository_root(document):
    text = document.read_text()
    assert "artifact/" not in text
    for entrypoint in re.findall(r"\b(?:python3|python|node)\s+(run\.py|src/[^\s]+)", text):
        assert (ROOT / entrypoint).is_file(), (document, entrypoint)
