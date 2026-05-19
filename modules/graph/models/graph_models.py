from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    properties: dict = field(default_factory=dict)
    style: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {"id": self.id, "type": self.type, "label": self.label}
        if self.properties:
            data["properties"] = self.properties
        if self.style:
            data["style"] = self.style
        return data


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    label: str | None = None
    properties: dict = field(default_factory=dict)
    style: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {"source": self.source, "target": self.target, "type": self.type}
        if self.label:
            data["label"] = self.label
        if self.properties:
            data["properties"] = self.properties
        if self.style:
            data["style"] = self.style
        return data
