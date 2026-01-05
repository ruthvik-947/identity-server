import pytest
from identity_server.schema import IdentityConfig, Interest

def test_identity_config_from_dict():
    data = {
        "name": "Test User",
        "background": {
            "summary": "A test user",
            "skills": ["python", "testing"],
        },
        "current_focus": ["Building things"],
        "interests": [
            {"topic": "music", "depth": "casual"},
        ],
        "privacy": {
            "public": ["name", "background"],
            "private": ["personal_notes"],
        },
    }
    config = IdentityConfig.from_dict(data)

    assert config.name == "Test User"
    assert config.background.summary == "A test user"
    assert config.background.skills == ["python", "testing"]
    assert config.current_focus == ["Building things"]
    assert len(config.interests) == 1
    assert config.interests[0].topic == "music"
    assert config.interests[0].depth == "casual"
    assert config.privacy.public == ["name", "background"]

def test_interest_depth_validation():
    with pytest.raises(ValueError):
        Interest(topic="test", depth="invalid")
