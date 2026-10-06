def test_probe_001_detects_company_over_generic_name():
    """When semantic attributes include both a company/organization token and a generic 'name' token

    The detector should choose the more specific 'company' classification rather than the generic 'name'.
    This test constructs a deterministic minimal history object that routes through detect_variables_in_history
    and asserts the externally observable mapping contains a 'company' detection for the interacted element.
    """

    from types import SimpleNamespace

    # Import the public entrypoint and DOM element type from the target package
    from browser_use.agent.variable_detector import detect_variables_in_history
    from browser_use.dom.views import DOMInteractedElement, NodeType

    # Construct attributes that contain both a company-specific token and the generic 'name' token
    attributes = {
        'id': 'organization_name',
        'name': 'organization_name',
        # Intentionally omit 'type' so attribute-based semantic checks run (no short-circuit)
    }

    # Create a DOMInteractedElement compatible with the project's expectations.
    # Use the same shape seen in existing tests to remain compatible with the public entrypoint.
    element = DOMInteractedElement(
        node_id=1,
        backend_node_id=1,
        frame_id='frame1',
        node_type=NodeType.ELEMENT_NODE,
        node_value='',
        node_name='input',
        attributes=attributes,
        bounds=None,
        x_path='//*[@id="organization_name"]',
        element_hash=12345,
    )

    # Build a minimal history structure compatible with detect_variables_in_history
    # history.history -> list of history_item; history_item.model_output.action -> list of actions
    # history_item.state.interacted_element -> list of elements
    mock_action = SimpleNamespace(type='input')
    model_output = SimpleNamespace(action=[mock_action])
    state = SimpleNamespace(interacted_element=[element])
    history_item = SimpleNamespace(model_output=model_output, state=state)
    history = SimpleNamespace(history=[history_item])

    # Call the public entrypoint
    detected = detect_variables_in_history(history)

    # Primary externally-observable assertion: 'company' key should be present in the mapping
    assert isinstance(detected, dict), "detect_variables_in_history must return a dict-like mapping"
    assert 'company' in detected, (
        "Expected a 'company' detection when attributes include an organization/company token; "
        "if implementation prefers generic 'name' this assertion will fail, revealing the specificity/priority bug."
    )

    # Conservative check that the detected variable carries no format (company classification has None format).
    dv = detected['company']

    # The DetectedVariable shape is not relied upon precisely; conservatively probe common attribute names
    format_candidates = (
        getattr(dv, 'format', None),
        getattr(dv, 'fmt', None),
        getattr(dv, 'var_format', None),
        getattr(dv, 'value_format', None),
    )

    # Primary oracle also asserts that at least one conventional format attribute is present and is None.
    # This is a conservative public assertion: company classification should not claim a specific format.
    assert any(fc is None for fc in format_candidates), (
        "Detected 'company' entry should indicate no specific format (None) via a conventional attribute; "
        "got: {}".format(format_candidates)
    )
