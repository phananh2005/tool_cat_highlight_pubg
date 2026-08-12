"""Data models cho PUBG Highlight Cutter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class Match:
    """Một game/match trong file livestream."""
    index: int
    start_time: float          # seconds từ đầu video
    end_time: float
    label: str = ""

    def __post_init__(self):
        if not self.label:
            self.label = f"Game {self.index + 1}"

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class Highlight:
    """Một khoảnh khắc highlight trong video."""
    start_time: float          # seconds từ đầu video
    end_time: float
    confidence: float = 1.0          # 0.0 - 1.0
    highlight_type: str = "manual"   # "kill", "audio_spike", "scene_change", "manual"
    match_index: int = 0             # thuộc game nào
    label: str = ""
    enabled: bool = True       # user có thể tắt mà không xóa

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class Project:
    """Toàn bộ dữ liệu 1 phiên làm việc."""
    source_file: str
    player_name: str = ""
    matches: list[Match] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)

    def highlights_for_match(self, match_index: int) -> list[Highlight]:
        """Lấy highlights thuộc 1 game, sắp xếp theo thời gian."""
        return sorted(
            [h for h in self.highlights if h.match_index == match_index],
            key=lambda h: h.start_time,
        )

    def save(self, path: str | Path):
        """Lưu project ra file JSON."""
        data = {
            "source_file": self.source_file,
            "player_name": self.player_name,
            "matches": [
                {"index": m.index, "start_time": m.start_time,
                 "end_time": m.end_time, "label": m.label}
                for m in self.matches
            ],
            "highlights": [
                {"start_time": h.start_time, "end_time": h.end_time,
                 "confidence": h.confidence, "highlight_type": h.highlight_type,
                 "match_index": h.match_index, "label": h.label,
                 "enabled": h.enabled}
                for h in self.highlights
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Project:
        """Đọc project từ file JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        proj = cls(source_file=data["source_file"], player_name=data.get("player_name", ""))
        proj.matches = [Match(**m) for m in data["matches"]]
        proj.highlights = [Highlight(**h) for h in data["highlights"]]
        return proj
