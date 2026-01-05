import pytest
from pathlib import Path
from identity_server.adapters.custom import CustomAdapter
from identity_server.sources import SourceConfig

@pytest.fixture
def custom_connector(tmp_path):
    connector = tmp_path / "connectors" / "test_connector.py"
    connector.parent.mkdir(parents=True)
    connector.write_text('''
def fetch(config):
    return [
        {"title": "Custom Item 1", "body": "Content 1", "tags": ["test"]},
        {"title": "Custom Item 2", "body": "Content 2", "tags": ["test"]},
    ]
''')
    return connector

def test_custom_adapter_loads_connector(custom_connector, tmp_path):
    config = SourceConfig(
        name="custom-test",
        type="custom",
        connector=str(custom_connector),
        config={"key": "value"},
        privacy="public",
    )
    adapter = CustomAdapter(config, base_path=tmp_path)
    items = adapter.fetch()

    assert len(items) == 2
    assert items[0].title == "Custom Item 1"
    assert items[0].source_name == "custom-test"
