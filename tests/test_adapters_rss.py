import pytest
from identity_server.adapters.rss import RSSAdapter
from identity_server.sources import SourceConfig

# We'll mock feedparser for testing
def test_rss_adapter_parse_entries(mocker):
    mock_feed = mocker.MagicMock()
    mock_feed.entries = [
        mocker.MagicMock(
            title="Article 1",
            summary="Summary of article 1",
            link="https://example.com/1",
            published_parsed=(2024, 1, 15, 12, 0, 0, 0, 0, 0),
        ),
        mocker.MagicMock(
            title="Article 2",
            summary="Summary of article 2",
            link="https://example.com/2",
            published_parsed=(2024, 1, 16, 12, 0, 0, 0, 0, 0),
        ),
    ]

    mocker.patch("feedparser.parse", return_value=mock_feed)

    config = SourceConfig(
        name="reading",
        type="rss",
        url="https://example.com/feed.xml",
        privacy="public",
    )
    adapter = RSSAdapter(config)
    items = adapter.fetch()

    assert len(items) == 2
    assert items[0].title == "Article 1"
    assert "Summary of article 1" in items[0].body
