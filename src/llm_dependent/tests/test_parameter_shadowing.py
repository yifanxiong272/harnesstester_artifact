"""Provider identity follows lexical bindings and actual parameter provenance."""

import os

import pytest

from llm_dependent.python.flow import analyze_flow_project_outputs
from python_reference import reference


CASES = [
    ("direct", "def run(completion):\n    return completion()\nrun(lambda: 'local')\n", 0, 1),
    ("keyword_only", "def run(*, completion):\n    return completion()\nrun(completion=lambda: 'local')\n", 0, 1),
    ("positional_only", "def run(completion, /):\n    return completion()\nrun(lambda: 'local')\n", 0, 1),
    ("closure", "def run(completion):\n    def inner():\n        return completion()\n    return inner()\n", 0, 1),
    ("namespace", "import litellm\ndef run(litellm):\n    return litellm.completion()\n", 0, 1),
    ("alias", "def run(completion):\n    alias = completion\n    return alias()\n", 0, 1),
    ("unshadowed", "def run():\n    return completion()\n", 1, 1),
    ("provider_argument", "def run(completion):\n    return completion()\ndef caller():\n    return run(completion)\n", 1, 1),
    ("provider_namespace_argument", "import litellm\ndef run(litellm):\n    return litellm.completion()\ndef caller():\n    return run(litellm)\n", 1, 1),
    ("provider_default", "def run(completion=completion):\n    return completion()\n", 1, 1),
    ("inner_binding", "def run(completion):\n    def inner():\n        from litellm import completion\n        return completion()\n    return inner()\n", 1, 1),
    ("sibling", "def local(completion):\n    return completion()\ndef remote():\n    return completion()\n", 1, 2),
    ("async", "async def run(completion):\n    return await completion()\n", 0, 1),
    ("vararg", "def run(*completion):\n    return completion[0]()\n", 0, 1),
    ("kwarg", "def run(**completion):\n    return completion['fn']()\n", 0, 0),
    ("provider_closure", "def run(completion):\n    def inner():\n        return completion()\n    return inner()\ndef caller():\n    return run(completion)\n", 1, 1),
    ("nearest_parameter", "def outer(completion=completion):\n    def middle(completion):\n        def inner():\n            return completion()\n        return inner()\n    return middle(lambda: 'local')\n", 0, 1),
    ("nearest_provider", "def outer(completion):\n    def middle(completion):\n        def inner():\n            return completion()\n        return inner()\n    from litellm import completion as provider\n    return middle(provider)\n", 1, 1),
]


@pytest.mark.parametrize("name,body,count,formal_count", CASES, ids=[c[0] for c in CASES])
def test_parameter_provider_binding(tmp_path, name, body, count, formal_count):
    source = tmp_path / "agent.py"
    source.write_text("from litellm import completion\n" + body)
    actual = analyze_flow_project_outputs(tmp_path, [source], "fixture")["none"]
    assert actual["fixed_point"]["converged"]
    assert len(actual["sources"]) == count
    if count == 0:
        assert actual["data_dependence"] == []
    if os.environ.get("LDH_FORMAL_ROOT"):
        expected = reference().analyze_flow_project_outputs(
            project_root=tmp_path, src_roots=[tmp_path], project_label="fixture",
        )["none"]
        assert len(expected["sources"]) == formal_count
        if count == formal_count:
            assert actual == expected


def test_parameter_type_and_return_annotation_keep_definition_scope(tmp_path):
    source = tmp_path / "agent.py"
    source.write_text("""from litellm import completion
class Client:
    def invoke(self):
        return completion()
def identity(Client: Client) -> Client:
    return Client
def run(client: Client):
    return identity(client).invoke()
""")
    from llm_dependent.python.flow.analysis import FlowAnalyzer
    analyzer = FlowAnalyzer(tmp_path, [source], "fixture")
    info = next(value for value in analyzer.index.functions.values() if value.name == "identity")
    assert {item.qualname for item in info.param_types["Client"]} == {"Client"}
    assert {item.qualname for item in info.return_types} == {"Client"}


@pytest.mark.parametrize("namespace,pass_provider", [(False, False), (False, True), (True, False)])
def test_imported_provider_facts_respect_parameter_scope(tmp_path, pass_provider, namespace):
    provider = tmp_path / "provider.py"
    provider.write_text("from openai import OpenAI\nclient = OpenAI()\n")
    source = tmp_path / "agent.py"
    binding = "provider" if namespace else "client"
    imported = "import provider" if namespace else "from provider import client"
    receiver = "provider.client" if namespace else "client"
    source.write_text(
        f"{imported}\n"
        f"def run({binding}):\n"
        "    def inner():\n"
        f"        return {receiver}.chat.completions.create(model='fixture')\n"
        "    return inner()\n"
        + (f"def caller():\n    return run({binding})\n" if pass_provider else "")
    )
    actual = analyze_flow_project_outputs(tmp_path, [source, provider], "fixture")["none"]
    assert len(actual["sources"]) == int(pass_provider)
    if not pass_provider:
        assert actual["data_dependence"] == []
    if os.environ.get("LDH_FORMAL_ROOT"):
        expected = reference().analyze_flow_project_outputs(
            project_root=tmp_path, src_roots=[tmp_path], project_label="fixture",
        )["none"]
        assert len(expected["sources"]) == 1
        if pass_provider:
            assert actual == expected


@pytest.mark.parametrize("namespace", [False, True])
def test_unmodeled_arguments_do_not_fall_back_to_same_named_import(tmp_path, namespace):
    """Module calls and project-module values do not currently propagate arguments."""
    provider = tmp_path / "provider.py"
    provider.write_text("from openai import OpenAI\nclient = OpenAI()\n")
    source = tmp_path / "agent.py"
    prefix = "import provider\n" if namespace else "from litellm import completion\n"
    imported = "provider" if namespace else "completion"
    call = "{}.client.chat.completions.create()" if namespace else "{}()"
    suffix = "def caller():\n    return run(provider)\n" if namespace else "run(completion)\n"
    for parameter in (imported, "fn"):
        source.write_text(prefix + f"def run({parameter}):\n    return {call.format(parameter)}\n" + suffix)
        actual = analyze_flow_project_outputs(tmp_path, [source, provider], "fixture")["none"]
        assert actual["sources"] == actual["data_dependence"] == []
        if os.environ.get("LDH_FORMAL_ROOT"):
            expected = reference().analyze_flow_project_outputs(
                project_root=tmp_path, src_roots=[tmp_path], project_label="fixture",
            )["none"]
            assert len(expected["sources"]) == int(parameter == imported)
            if parameter == "fn":
                assert actual == expected
