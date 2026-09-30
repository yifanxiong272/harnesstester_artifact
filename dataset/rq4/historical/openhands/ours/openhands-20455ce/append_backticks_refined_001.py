from openhands.agenthub.browsing_agent.response_parser import BrowsingResponseParser


def test_generated_target_probe_asset_004_append_only_backticks():
    parser = BrowsingResponseParser()
    content = "click('81')"
    response = {'choices': [{'message': {'content': content}}]}
    result = parser.parse_response(response)
    # Primary oracle: must append exactly three backticks to the original content
    assert result == content + '```'
