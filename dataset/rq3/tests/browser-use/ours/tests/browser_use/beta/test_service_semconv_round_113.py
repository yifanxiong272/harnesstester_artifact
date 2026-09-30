import pytest

from browser_use.beta import service


def test_non_dict_input_round_113():
    # non-dict input should be converted to a text content with str(part)
    res = service._terminal_laminar_semconv_content_part(123)
    assert isinstance(res, dict)
    assert res == {"type": "text", "content": "123"}


def test_text_part_string_round_113():
    part = {"type": "text", "text": "hello world"}
    res = service._terminal_laminar_semconv_content_part(part)
    assert res == {"type": "text", "content": "hello world"}


def test_image_url_data_inline_true_round_113():
    # data URL with inline_image_data True should return blob with mimeType and blob
    blob_payload = "AAAA"
    data_url = f"data:image/png;base64,{blob_payload}"
    part = {"type": "image_url", "image_url": {"url": data_url}}
    res = service._terminal_laminar_semconv_content_part(part, inline_image_data=True)
    assert res["type"] == "blob"
    assert res.get("blob") == blob_payload
    assert res.get("mimeType") == "image/png"


def test_image_url_data_inline_false_round_113():
    # data URL with inline_image_data False should return a placeholder content (no blob)
    blob_payload = "BBBB"
    data_url = f"data:image/jpeg;base64,{blob_payload}"
    part = {"type": "image_url", "image_url": {"url": data_url}}
    res = service._terminal_laminar_semconv_content_part(part, inline_image_data=False)
    assert res["type"] == "blob"
    # when not inlining the blob, content should be placeholder and mimeType set
    assert res.get("content") == "[image in span input]"
    assert res.get("mimeType") == "image/jpeg"


def test_image_url_uri_round_113():
    # normal uri (non-data) should be returned as a uri type
    url = "https://example.com/image.png"
    part = {"type": "image_url", "image_url": {"url": url}}
    res = service._terminal_laminar_semconv_content_part(part)
    assert res == {"type": "uri", "uri": url}


def test_tool_call_and_arguments_round_113():
    # tool_call/tool_use path should copy id, name and arguments when present
    part = {"type": "tool_call", "id": "tool-1", "name": "search", "arguments": {"q": "x"}}
    res = service._terminal_laminar_semconv_content_part(part)
    assert res["type"] == "tool_call"
    assert res["id"] == "tool-1"
    assert res["name"] == "search"
    assert res["arguments"] == {"q": "x"}


def test_tool_result_with_id_and_content_round_113():
    # tool_result path should produce tool_call_response with id and response
    part = {"type": "tool_result", "tool_call_id": "call-42", "content": {"ok": True}}
    res = service._terminal_laminar_semconv_content_part(part)
    assert res["type"] == "tool_call_response"
    assert res["id"] == "call-42"
    assert res["response"] == {"ok": True}


def test_nonstring_content_uses_json_attribute_round_113():
    # when content is not a string, the function falls back to _terminal_laminar_json_attribute
    part = {"type": "custom", "foo": [1, 2, 3]}
    res = service._terminal_laminar_semconv_content_part(part)
    # expected content is whatever the helper produces for this part object
    expected = service._terminal_laminar_json_attribute(part)
    assert res == {"type": "text", "content": expected}
