"""Гео-маппинг транзакция -> здание по названию.

Самая рискованная часть пайплайна, поэтому три исхода:
  score >= 92  -> auto (принимаем)
  75 <= score < 92 -> review (в очередь ручной валидации)
  score < 75   -> unmatched (не привязываем)
"""
from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import text
from sqlalchemy.orm import Session

AUTO_THRESHOLD = 92
REVIEW_THRESHOLD = 75


def classify_score(score: float) -> str:
    if score >= AUTO_THRESHOLD:
        return "auto"
    if score >= REVIEW_THRESHOLD:
        return "review"
    return "unmatched"


@dataclass
class MatchResult:
    building_id: int | None
    score: float
    status: str  # auto | review | unmatched


def normalize_name(name: str) -> str:
    return " ".join(name.lower().replace("-", " ").split())


class BuildingMatcher:
    """Держит алиасы в памяти: exact-совпадение, иначе rapidfuzz по всем алиасам."""

    def __init__(self, db: Session):
        rows = db.execute(text("SELECT alias, building_id FROM building_aliases")).all()
        self._aliases: dict[str, int] = {normalize_name(a): b for a, b in rows}
        self._keys = list(self._aliases.keys())
        # В bulk CSV миллионы строк, но уникальных названий на порядки меньше —
        # без кэша fuzzy-поиск по каждой строке делает загрузку неподъёмной
        self._cache: dict[str, MatchResult] = {}

    def match(self, name: str | None) -> MatchResult:
        if not name or not self._keys:
            return MatchResult(None, 0.0, "unmatched")
        norm = normalize_name(name)

        cached = self._cache.get(norm)
        if cached is not None:
            return cached

        if norm in self._aliases:
            result = MatchResult(self._aliases[norm], 100.0, "auto")
        else:
            best = process.extractOne(norm, self._keys, scorer=fuzz.WRatio)
            if best is None:
                result = MatchResult(None, 0.0, "unmatched")
            else:
                alias, score, _ = best
                status = classify_score(score)
                building_id = self._aliases[alias] if status != "unmatched" else None
                result = MatchResult(building_id, float(score), status)
        self._cache[norm] = result
        return result
