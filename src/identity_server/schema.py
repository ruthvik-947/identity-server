from dataclasses import dataclass, field
from typing import Literal

DepthLevel = Literal["casual", "engaged", "deep"]

@dataclass
class Interest:
    topic: str
    depth: DepthLevel

    def __post_init__(self):
        if self.depth not in ("casual", "engaged", "deep"):
            raise ValueError(f"Invalid depth: {self.depth}")

@dataclass
class Background:
    summary: str = ""
    skills: list[str] = field(default_factory=list)

@dataclass
class Privacy:
    public: list[str] = field(default_factory=list)
    private: list[str] = field(default_factory=list)

@dataclass
class IdentityConfig:
    name: str
    pronouns: str | None = None
    background: Background = field(default_factory=Background)
    current_focus: list[str] = field(default_factory=list)
    interests: list[Interest] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    privacy: Privacy = field(default_factory=Privacy)

    @classmethod
    def from_dict(cls, data: dict) -> "IdentityConfig":
        background = Background(**data.get("background", {}))
        privacy = Privacy(**data.get("privacy", {}))
        interests = [
            Interest(**i) for i in data.get("interests", [])
        ]
        return cls(
            name=data["name"],
            pronouns=data.get("pronouns"),
            background=background,
            current_focus=data.get("current_focus", []),
            interests=interests,
            values=data.get("values", []),
            privacy=privacy,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pronouns": self.pronouns,
            "background": {
                "summary": self.background.summary,
                "skills": self.background.skills,
            },
            "current_focus": self.current_focus,
            "interests": [
                {"topic": i.topic, "depth": i.depth}
                for i in self.interests
            ],
            "values": self.values,
            "privacy": {
                "public": self.privacy.public,
                "private": self.privacy.private,
            },
        }
