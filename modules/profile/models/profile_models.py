from dataclasses import dataclass, field


@dataclass
class TimelineEvent:
    time: str
    type: str
    title: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "type": self.type,
            "title": self.title,
            "detail": self.detail,
        }


@dataclass
class ProfileSection:
    name: str
    data: dict | list

    def to_dict(self) -> dict:
        return {"name": self.name, "data": self.data}
