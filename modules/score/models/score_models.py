from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    zjhm: str
    total_score: int
    risk_level: str
    dim_case: int = 0
    dim_behavior: int = 0
    dim_family: int = 0
    dim_education: int = 0
    dim_social: int = 0
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "zjhm": self.zjhm,
            "total_score": self.total_score,
            "risk_level": self.risk_level,
            "dim_case": self.dim_case,
            "dim_behavior": self.dim_behavior,
            "dim_family": self.dim_family,
            "dim_education": self.dim_education,
            "dim_social": self.dim_social,
            "detail": self.detail,
        }
