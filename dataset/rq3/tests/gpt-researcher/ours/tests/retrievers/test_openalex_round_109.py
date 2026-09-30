from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


def test_prefers_pdf_round_109():
    # When a PDF URL is present in best_oa_location, it should be returned
    result = {
        "best_oa_location": {"pdf_url": "http://example.com/doc.pdf"},
        "primary_location": {"landing_page_url": "http://example.com/landing"},
        "id": "https://openalex.org/W1",
    }

    href = OpenAlexSearch._pick_href(result)

    assert href == "http://example.com/doc.pdf"


def test_falls_back_to_landing_when_pdf_missing_round_109():
    # When pdf_url is falsy/absent, prefer primary_location.landing_page_url
    result_with_empty_pdf = {
        "best_oa_location": {"pdf_url": ""},
        "primary_location": {"landing_page_url": "http://example.com/landing"},
        "id": "irrelevant",
    }
    href = OpenAlexSearch._pick_href(result_with_empty_pdf)
    assert href == "http://example.com/landing"

    # Also cover the case where best_oa_location is missing entirely
    result_no_best = {
        "primary_location": {"landing_page_url": "http://example.com/landing2"},
        "id": "irrelevant",
    }
    href2 = OpenAlexSearch._pick_href(result_no_best)
    assert href2 == "http://example.com/landing2"


def test_falls_back_to_id_when_no_pdf_or_landing_round_109():
    # When neither pdf_url nor landing_page_url are present, return the work id
    result = {
        "best_oa_location": {},
        "primary_location": {},
        "id": "https://openalex.org/W2",
    }

    href = OpenAlexSearch._pick_href(result)

    assert href == "https://openalex.org/W2"


def test_handles_missing_keys_round_109():
    # If result lacks all keys, function should safely return None
    empty_result = {}
    href = OpenAlexSearch._pick_href(empty_result)
    assert href is None
