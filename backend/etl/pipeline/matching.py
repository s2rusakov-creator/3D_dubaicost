"""Гео-маппинг транзакция -> здание по названию.

Самая рискованная часть пайплайна, поэтому три исхода:
  score >= 92  -> auto (принимаем)
  75 <= score < 92 -> review (в очередь ручной валидации)
  score < 75   -> unmatched (не привязываем)
"""
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import text
from sqlalchemy.orm import Session

AUTO_THRESHOLD = 92
REVIEW_THRESHOLD = 75

# WRatio завышает скор коротких/общих алиасов: любое DLD-название,
# содержащее слово "Residence"/"Villa" и т.п., "матчится" на первое здание
# с таким алиасом почти со 100% score, хотя это не одно и то же здание.
# Плюс мусорные OSM-теги подобъектов (парковки, кода блоков): "A", "01", "G24".
MIN_ALIAS_LENGTH = 4
_GENERIC_ALIASES = {
    "residence", "residences", "tower", "towers", "hotel", "hotels",
    "house", "building", "villa", "villas", "plaza", "one", "two",
    "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "spa", "office", "offices", "apartment", "apartments", "block",
    "parking", "mall", "center", "centre", "club",
}
# Родовое ведущее слово: "Tower 1", "Building 10", "Block B", "Podium A" —
# это подобъект/этаж/секция в OSM, а не уникальное здание. Через общие токены
# ("tower"+"1") такой алиас ловит десятки чужих DLD-транзакций ("Modelux Tower 1",
# "Sunrise Bay Tower 1" -> "Tower 1"). Отсекаем. Проприетарные имена вида
# "Bahar 1", "Al Majara 2" НЕ трогаем (ведущее слово не родовое).
_GENERIC_LEAD = {
    "tower", "towers", "building", "buildings", "block", "blocks",
    "podium", "plot", "plots", "floor", "villa", "villas", "unit", "units",
    "wing", "phase", "zone", "cluster", "core",
}
_CODE_PATTERN = re.compile(r"^[a-z]{0,2}\d+[a-z]{0,2}$")
# Короткий код: "1", "10", "2a" (буква-цифра) ИЛИ 1–2 буквы ("a", "b", "ab").
_SHORT_CODE = re.compile(r"^([a-z]{0,2}\d+[a-z]{0,2}|[a-z]{1,2})$")


def is_low_quality_alias(alias: str) -> bool:
    norm = normalize_name(alias)
    stripped = norm.replace(" ", "")
    if len(norm) < MIN_ALIAS_LENGTH:
        return True
    if norm in _GENERIC_ALIASES:
        return True
    if _CODE_PATTERN.match(stripped):
        return True
    parts = norm.split()
    if len(parts) == 2 and parts[0] in _GENERIC_LEAD and _SHORT_CODE.match(parts[1]):
        return True
    return False


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
        self._aliases: dict[str, int] = {
            normalize_name(a): b for a, b in rows if not is_low_quality_alias(a)
        }
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
            # WRatio быстро сужает до кандидатов, но склонен завышать скор при
            # совпадении лишь общего токена (бренд-девелопер, номер). Гейт по
            # token_set_ratio: берём min(WRatio, token_set) — чтобы пройти в auto,
            # названия должны совпадать И по строке, И по набору слов.
            candidates = process.extract(norm, self._keys, scorer=fuzz.WRatio, limit=3)
            best_alias, best_score = None, 0.0
            for alias, wr, _ in candidates:
                combined = min(wr, fuzz.token_set_ratio(norm, alias))
                if combined > best_score:
                    best_alias, best_score = alias, combined
            if best_alias is None:
                result = MatchResult(None, 0.0, "unmatched")
            else:
                status = classify_score(best_score)
                building_id = self._aliases[best_alias] if status != "unmatched" else None
                result = MatchResult(building_id, float(best_score), status)
        self._cache[norm] = result
        return result
