from backend.service.application_task_metadata import title_from_harbor_task_name


def test_title_from_harbor_task_name():
    # The application-type prefix is metadata (``metadata.type``), so display
    # titles drop it instead of repeating it.
    assert (
        title_from_harbor_task_name("application/web-playwright-quote-choice")
        == "Playwright Quote Choice"
    )
    assert (
        title_from_harbor_task_name("application/survey-nike-air-max-dn")
        == "Nike Air Max Dn"
    )
    assert (
        title_from_harbor_task_name("application/survey-product-feedback")
        == "Product Feedback"
    )
    assert title_from_harbor_task_name("application/chat-recai") == "RecAI"
    assert (
        title_from_harbor_task_name("application/chat-multi-agent-medical-assistant")
        == "Multi Agent Medical Assistant"
    )
    assert title_from_harbor_task_name("application/chat-openbb") == "OpenBB"
    assert (
        title_from_harbor_task_name("application/os-app-macos-stocks-mu-sentiment")
        == "Stocks MU Sentiment"
    )
    # Legacy Harbor names still parse.
    assert title_from_harbor_task_name("matraix/application-chat-recai") == "RecAI"
