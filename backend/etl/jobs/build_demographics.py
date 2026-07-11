"""Строит демографический слой по районам (ориентировочный).

ВАЖНО про данные: официальная статистика DSC публикуется по официальным
названиям общин ("Marsa Dubai" вместо "Dubai Marina") — сопоставить точные
цифры населения с маркетинговыми районами чисто нельзя, поэтому население
здесь НЕ заполняется (не выдумываем числа). Слой отражает ОРИЕНТИРОВОЧНЫЕ
диаспоры по районам из открытых источников (tenchat.ru, dzen.ru, volna.me,
emirate-dubai.com, kommersant.ru) — это тенденции, не официальная статистика,
и в UI помечается соответствующе (is_indicative=true).

Геометрия зоны = выпуклая оболочка реально загруженных зданий района
(ST_ConvexHull) — без отдельного запроса полигонов.

Запуск: python -m etl.jobs.build_demographics
"""
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging

log = get_logger(__name__)

INDICATIVE_SOURCES = (
    "tenchat.ru, dzen.ru, volna.me, emirate-dubai.com, kommersant.ru, "
    "propertyfinder.ae, bayut.com, drivenproperties.com, engelvoelkers.com "
    "(ориентировочно, не офиц. статистика)"
)

# bbox: (min_lon, min_lat, max_lon, max_lat) — порядок ST_MakeEnvelope
ZONES = [
    {
        "name_en": "Deira",
        "bbox": (55.300, 25.250, 55.335, 25.290),
        "dominant_community": "south_asian",
        "communities": "Индийцы, пакистанцы, иранцы — рынки, этнические магазины, доступное жильё",
        "note": "Исторический торговый район; выражены южноазиатская и иранская диаспоры",
    },
    {
        "name_en": "Bur Dubai",
        "bbox": (55.280, 25.240, 55.310, 25.275),
        "dominant_community": "south_asian",
        "communities": "Индийцы, пакистанцы, бангладешцы — исторический центр, доступное жильё",
        "note": "Старый Дубай; преимущественно южноазиатские общины",
    },
    {
        "name_en": "International City",
        "bbox": (55.395, 25.155, 55.425, 25.185),
        "dominant_community": "filipino_chinese_mixed",
        "communities": "Филиппинцы, китайцы, арабы — недорогое жильё, тематические кластеры",
        "note": "Кластерная застройка; смешанные диаспоры",
    },
    {
        "name_en": "Dubai Marina",
        "bbox": (55.125, 25.070, 55.150, 25.095),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — премиальные апартаменты у воды",
        "note": "Динамичная престижная локация; западные и русскоязычные экспаты",
    },
    {
        "name_en": "Downtown Dubai",
        "bbox": (55.270, 25.185, 55.290, 25.205),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — премиальный центр",
        "note": "Флагманский центр (Burj Khalifa, Dubai Mall); состоятельные экспаты",
    },
    {
        "name_en": "Jumeirah Beach Residence (JBR)",
        "bbox": (55.128, 25.068, 55.145, 25.085),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — жильё на пляже",
        "note": "Пляжная престижная локация; западные и русскоязычные экспаты",
    },
    {
        "name_en": "Jumeirah",
        "bbox": (55.240, 25.195, 55.275, 25.245),
        "dominant_community": "emirati_affluent",
        "communities": "Граждане ОАЭ и состоятельные экспаты — вилльная застройка",
        "note": "Престижный вилльный район; граждане ОАЭ и обеспеченные экспаты",
    },
    {
        "name_en": "Palm Jumeirah",
        "bbox": (55.110, 25.100, 55.160, 25.135),
        "dominant_community": "emirati_affluent",
        "communities": "Граждане ОАЭ и состоятельные экспаты — виллы и премиум-апартаменты",
        "note": "Насыпной остров; премиальная недвижимость",
    },
    # Расширение: новые районы (по открытым источникам о расселении общин)
    {
        "name_en": "Al Karama",
        "bbox": (55.298, 25.243, 55.315, 25.258),
        "dominant_community": "south_asian",
        "communities": "Индийцы, филиппинцы, пакистанцы — доступное жильё, рынки, рестораны",
        "note": "Плотный центральный район; давняя индийская и филиппинская общины",
    },
    {
        "name_en": "Al Satwa",
        "bbox": (55.255, 25.218, 55.278, 25.238),
        "dominant_community": "filipino_chinese_mixed",
        "communities": "Филиппинцы, южноазиаты — компактный старый район, доступно, центрально",
        "note": "Старый малоэтажный район; сильная филиппинская община",
    },
    {
        "name_en": "Jumeirah Lakes Towers (JLT)",
        "bbox": (55.135, 25.060, 55.155, 25.082),
        "dominant_community": "western_russian_expats",
        "communities": "Западные, русскоязычные, индийские профессионалы — башни у озёр",
        "note": "Деловой апарт-район рядом с Marina; много экспатов-профессионалов",
    },
    {
        "name_en": "Business Bay",
        "bbox": (55.255, 25.180, 55.278, 25.200),
        "dominant_community": "mixed_diverse",
        "communities": "Многонациональные профессионалы — европейцы, арабы, индийцы, иранцы",
        "note": "Деловой центр у канала; очень смешанный состав",
    },
    {
        "name_en": "Jumeirah Village Circle (JVC)",
        "bbox": (55.200, 25.050, 55.222, 25.072),
        "dominant_community": "south_asian",
        "communities": "Индийские семьи и смешанные общины — доступные апартаменты и таунхаусы",
        "note": "Популярен у индийских семей (школы, парки); доступное жильё",
    },
    {
        "name_en": "Discovery Gardens",
        "bbox": (55.130, 25.035, 55.150, 25.055),
        "dominant_community": "south_asian",
        "communities": "Пакистанцы, бангладешцы, индийцы — доступные студии/апартаменты",
        "note": "Бюджетная застройка; преимущественно южноазиатские общины",
    },
    {
        "name_en": "Dubai Silicon Oasis",
        "bbox": (55.373, 25.108, 55.400, 25.132),
        "dominant_community": "mixed_diverse",
        "communities": "Индийские IT-специалисты и очень смешанный состав — техно-кластер",
        "note": "Технопарк с жильём; одна из самых многонациональных зон",
    },
    {
        "name_en": "Al Nahda",
        "bbox": (55.365, 25.278, 55.392, 25.300),
        "dominant_community": "south_asian",
        "communities": "Индийцы и южноазиаты — доступно, у границы Шарджи, метро",
        "note": "Плотный район у Шарджи; крупная индийская община",
    },
    {
        "name_en": "Mirdif",
        "bbox": (55.415, 25.208, 55.448, 25.238),
        "dominant_community": "emirati_affluent",
        "communities": "Граждане ОАЭ, арабские семьи и западные экспаты — виллы, семейный район",
        "note": "Малоэтажный семейный район; эмиратцы, арабы, западные экспаты",
    },
    {
        "name_en": "The Greens / The Views",
        "bbox": (55.163, 25.093, 55.185, 25.112),
        "dominant_community": "western_russian_expats",
        "communities": "Западные профессионалы и экспаты — зелёные апарт-комплексы",
        "note": "Спокойный апарт-район; преимущественно западные экспаты",
    },
    {
        "name_en": "Al Barsha",
        "bbox": (55.188, 25.100, 55.215, 25.122),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — арабы, южноазиаты, филиппинцы, западные",
        "note": "Центральный многофункциональный район; очень смешанный",
    },
    # Вторая волна: villa-пояса, Dubailand, северные и центральные районы
    {
        "name_en": "Arabian Ranches",
        "bbox": (55.255, 25.045, 55.290, 25.075),
        "dominant_community": "western_russian_expats",
        "communities": "Западные (британские) семьи и состоятельные экспаты — виллы",
        "note": "Один из первых вилльных фрихолдов; британские/западные семьи",
    },
    {
        "name_en": "Dubai Hills Estate",
        "bbox": (55.245, 25.100, 55.280, 25.130),
        "dominant_community": "western_russian_expats",
        "communities": "Западные семьи и состоятельные экспаты — виллы и апартаменты у гольфа",
        "note": "Премиальный семейный район; западные экспаты",
    },
    {
        "name_en": "The Springs / Meadows",
        "bbox": (55.155, 25.055, 55.190, 25.085),
        "dominant_community": "western_russian_expats",
        "communities": "Западные (британские) семьи — таунхаусы и виллы (Emirates Living)",
        "note": "Семейный вилльный пояс; преимущественно западные экспаты",
    },
    {
        "name_en": "Emirates Hills",
        "bbox": (55.155, 25.070, 55.178, 25.092),
        "dominant_community": "emirati_affluent",
        "communities": "Состоятельные — эмиратцы, западные, арабские и азиатские элиты",
        "note": "Ультра-премиальные виллы; состоятельный смешанный состав",
    },
    {
        "name_en": "Jumeirah Golf Estates",
        "bbox": (55.185, 25.045, 55.215, 25.075),
        "dominant_community": "western_russian_expats",
        "communities": "Западные экспаты-семьи — виллы у гольф-полей",
        "note": "Фрихолд-гольф-сообщество; западные экспаты",
    },
    {
        "name_en": "Jumeirah Islands",
        "bbox": (55.145, 25.055, 55.168, 25.078),
        "dominant_community": "western_russian_expats",
        "communities": "Западные и состоятельные экспаты — виллы на островках",
        "note": "Премиальный вилльный анклав; западные экспаты",
    },
    {
        "name_en": "Motor City",
        "bbox": (55.228, 25.040, 55.252, 25.065),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — семьи и холостяки, без доминирующей нации",
        "note": "Доступный семейный район (Dubailand); очень смешанный",
    },
    {
        "name_en": "Dubai Sports City",
        "bbox": (55.208, 25.030, 55.235, 25.055),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — доступные апартаменты, молодые экспаты",
        "note": "Спортивный кластер (Dubailand); смешанный, бюджетный",
    },
    {
        "name_en": "Arjan",
        "bbox": (55.232, 25.058, 55.256, 25.080),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — экспаты и локалы, растущий район",
        "note": "Развивающийся район Dubailand; смешанный",
    },
    {
        "name_en": "Jumeirah Village Triangle (JVT)",
        "bbox": (55.182, 25.045, 55.205, 25.068),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — доступные виллы и таунхаусы",
        "note": "Доступное семейное сообщество; смешанный",
    },
    {
        "name_en": "Al Furjan",
        "bbox": (55.140, 25.018, 55.168, 25.045),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — южноазиаты, арабы, западные, семьи",
        "note": "Растущий район у метро; смешанный",
    },
    {
        "name_en": "Town Square (Nshama)",
        "bbox": (55.245, 24.988, 55.278, 25.018),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — доступные апартаменты и таунхаусы, молодые семьи",
        "note": "Бюджетное семейное сообщество; смешанный",
    },
    {
        "name_en": "Mudon",
        "bbox": (55.255, 25.028, 55.288, 25.055),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — виллы/таунхаусы, семьи",
        "note": "Семейное вилльное сообщество (Dubailand); смешанный",
    },
    {
        "name_en": "Dubai Production City (IMPZ)",
        "bbox": (55.180, 25.018, 55.208, 25.045),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — доступные апартаменты, экспаты",
        "note": "Медиа/производственный кластер с жильём; смешанный",
    },
    {
        "name_en": "Al Qusais",
        "bbox": (55.375, 25.272, 55.408, 25.300),
        "dominant_community": "south_asian",
        "communities": "Южноазиаты, филиппинцы, арабы — доступно, у Шарджи, метро",
        "note": "Плотный северный район; крупные азиатские общины",
    },
    {
        "name_en": "Muhaisnah",
        "bbox": (55.418, 25.268, 55.452, 25.300),
        "dominant_community": "south_asian",
        "communities": "Южноазиаты (в т.ч. рабочие Sonapur), арабы — самый населённый район",
        "note": "Самое населённое сообщество Дубая (~235k); южноазиатское",
    },
    {
        "name_en": "Al Warqa",
        "bbox": (55.448, 25.168, 55.488, 25.202),
        "dominant_community": "mixed_diverse",
        "communities": "Локалы, арабы и азиатские экспаты — виллы и апартаменты",
        "note": "Спокойный семейный район; эмиратцы, арабы, азиаты",
    },
    {
        "name_en": "Al Rashidiya",
        "bbox": (55.382, 25.212, 55.412, 25.242),
        "dominant_community": "emirati_affluent",
        "communities": "Эмиратцы и состоятельные экспаты — виллы",
        "note": "Обеспеченный смешанный район; эмиратцы и экспаты",
    },
    {
        "name_en": "Al Khawaneej",
        "bbox": (55.462, 25.208, 55.500, 25.242),
        "dominant_community": "emirati_affluent",
        "communities": "Преимущественно эмиратцы — просторные виллы, фермы",
        "note": "Традиционный эмиратский вилльный район",
    },
    {
        "name_en": "Nad Al Sheba",
        "bbox": (55.308, 25.150, 55.345, 25.192),
        "dominant_community": "emirati_affluent",
        "communities": "Эмиратцы и состоятельные экспаты — виллы у Meydan",
        "note": "Эмиратский вилльный район рядом с Meydan",
    },
    {
        "name_en": "DIFC",
        "bbox": (55.272, 25.205, 55.292, 25.222),
        "dominant_community": "western_russian_expats",
        "communities": "Западные и международные финансовые профессионалы — премиум-башни",
        "note": "Финансовый центр; профессионалы и инвесторы",
    },
    {
        "name_en": "City Walk / Al Wasl",
        "bbox": (55.252, 25.202, 55.278, 25.228),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — молодые профессионалы, семьи, экспаты",
        "note": "Современный городской район; смешанный, семейный",
    },
    {
        "name_en": "Barsha Heights (Tecom)",
        "bbox": (55.168, 25.093, 55.192, 25.115),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — молодые профессионалы (у Media/Internet City)",
        "note": "Центральный апарт-район; молодые профессионалы, смешанный",
    },
    {
        "name_en": "Meydan / MBR City",
        "bbox": (55.288, 25.158, 55.322, 25.192),
        "dominant_community": "emirati_affluent",
        "communities": "Эмиратцы и состоятельные экспаты — новые премиальные виллы/апартаменты",
        "note": "Новый премиальный район у ипподрома; состоятельный",
    },
    {
        "name_en": "Umm Suqeim",
        "bbox": (55.195, 25.138, 55.222, 25.165),
        "dominant_community": "emirati_affluent",
        "communities": "Эмиратцы и состоятельные экспаты — виллы у побережья",
        "note": "Прибрежный вилльный район; эмиратцы и обеспеченные экспаты",
    },
    {
        "name_en": "Al Sufouh",
        "bbox": (55.155, 25.098, 55.188, 25.128),
        "dominant_community": "western_russian_expats",
        "communities": "Западные экспаты и состоятельные — виллы/апартаменты у Media City",
        "note": "Прибрежный район между Marina и Jumeirah; западные экспаты",
    },
    # Третья волна: добор оставшихся заметных жилых зон
    {
        "name_en": "Oud Metha / Umm Hurair",
        "bbox": (55.310, 25.228, 55.335, 25.252),
        "dominant_community": "south_asian",
        "communities": "Индийцы и южноазиаты — устоявшийся район, школы, больницы",
        "note": "Центральный район у Bur Dubai; южноазиатские общины",
    },
    {
        "name_en": "Al Jaddaf",
        "bbox": (55.315, 25.215, 55.340, 25.238),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — новые башни у ручья, экспаты",
        "note": "Развивающийся район у Creek; смешанный",
    },
    {
        "name_en": "Dubai Festival City",
        "bbox": (55.345, 25.215, 55.375, 25.245),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — семьи и экспаты у ручья",
        "note": "Многофункциональный район у Creek; смешанный",
    },
    {
        "name_en": "Dubai Creek Harbour",
        "bbox": (55.335, 25.195, 55.365, 25.220),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — новые премиальные башни, экспаты",
        "note": "Новый прибрежный район; смешанный, растущий",
    },
    {
        "name_en": "Za'abeel",
        "bbox": (55.288, 25.215, 55.315, 25.245),
        "dominant_community": "emirati_affluent",
        "communities": "Эмиратцы и госструктуры — виллы, дворцовая зона",
        "note": "Центральный эмиратский район рядом с Downtown",
    },
    {
        "name_en": "Green Community / DIP",
        "bbox": (55.150, 24.965, 55.185, 25.000),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — экспаты-семьи, зелёные виллы (Dubai Investment Park)",
        "note": "Тихий район на юго-западе; смешанный",
    },
    {
        "name_en": "Liwan",
        "bbox": (55.310, 25.115, 55.340, 25.145),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — доступные апартаменты, экспаты",
        "note": "Доступный район Dubailand; смешанный",
    },
    {
        "name_en": "Bluewaters Island",
        "bbox": (55.115, 25.075, 55.135, 25.092),
        "dominant_community": "western_russian_expats",
        "communities": "Западные и состоятельные экспаты — премиум-апартаменты у Ain Dubai",
        "note": "Насыпной остров у JBR; состоятельные экспаты",
    },
    {
        "name_en": "Al Quoz",
        "bbox": (55.225, 25.135, 55.255, 25.160),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — южноазиаты, рабочие, арт-кластеры",
        "note": "Промышленно-жилой район; преимущественно азиатские общины",
    },
    {
        "name_en": "Academic City / Dubailand Residence",
        "bbox": (55.400, 25.108, 55.435, 25.140),
        "dominant_community": "mixed_diverse",
        "communities": "Смешанный состав — студенты и молодые экспаты, доступное жильё",
        "note": "Кластер университетов с жильём; очень смешанный",
    },
]

UPSERT = text(
    """
    INSERT INTO district_demographics
        (name_en, geom, dominant_community, communities, note, sources, is_indicative)
    VALUES (
        :name, ST_Multi(:hull)::geometry(MultiPolygon, 4326),
        :dominant, :communities, :note, :sources, true
    )
    ON CONFLICT (name_en) DO UPDATE SET
        geom = EXCLUDED.geom,
        dominant_community = EXCLUDED.dominant_community,
        communities = EXCLUDED.communities,
        note = EXCLUDED.note,
        sources = EXCLUDED.sources,
        updated_at = now()
    """
)

# Оболочка зданий района: ST_ConvexHull даёт устойчивый полигон вокруг
# застройки. NULL если в bbox не оказалось зданий.
HULL = text(
    """
    SELECT ST_ConvexHull(ST_Collect(geom)) AS hull
    FROM buildings
    WHERE geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
    """
)


def main() -> None:
    setup_logging()
    db = SessionLocal()
    built = 0
    try:
        for z in ZONES:
            minx, miny, maxx, maxy = z["bbox"]
            row = db.execute(
                HULL, {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
            ).first()
            hull_wkb = row.hull if row else None
            if hull_wkb is None:
                log.warning("zone_no_buildings", zone=z["name_en"])
                continue
            db.execute(
                UPSERT,
                {
                    "name": z["name_en"],
                    "hull": hull_wkb,
                    "dominant": z["dominant_community"],
                    "communities": z["communities"],
                    "note": z["note"],
                    "sources": INDICATIVE_SOURCES,
                },
            )
            built += 1
        db.commit()
        log.info("demographics_built", zones=built)
    finally:
        db.close()


if __name__ == "__main__":
    main()
