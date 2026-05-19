from dataclasses import dataclass


@dataclass
class DashboardItem:
    label: str
    value: int | float

    def to_dict(self) -> dict:
        return {"label": self.label, "value": self.value}


@dataclass
class HeatmapPoint:
    lng: float
    lat: float
    weight: int

    def to_dict(self) -> dict:
        return {"lng": self.lng, "lat": self.lat, "weight": self.weight}
