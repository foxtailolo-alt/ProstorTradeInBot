from __future__ import annotations

import httpx

from src.domain.enums import SupportedCategory
from src.parser.damprodam import DamProdamApiClient, DamProdamSnapshotImporter


async def test_importer_builds_snapshot_from_api_payloads() -> None:
    payloads = {
        "https://damprodam.ru/py/iphone_buyout/params": [
            {
                "device_abbr": "iphone15",
                "device_name": "iPhone 15",
                "seq_position": 2,
                "params": {
                    "color": {
                        "group_name": "Цвет",
                        "group_abbr": "color",
                        "vals": [
                            {"name": "Black", "abbr": "black"},
                            {"name": "Blue", "abbr": "blue"},
                        ],
                    },
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": [
                            {"name": "128 ГБ", "abbr": "128"},
                            {"name": "256 ГБ", "abbr": "256"},
                        ],
                    },
                },
            }
        ],
        "https://damprodam.ru/py/macbook_buyout/params": {
            "macbookair": {
                "device_abbr": "macbookair",
                "device_name": "MacBook Air",
                "seq_position": 1,
                "params": {
                    "year": {
                        "group_name": "Год",
                        "group_abbr": "year",
                        "vals": [2015, 2016, 2021],
                    },
                    "cpu": {
                        "group_name": "Процессор",
                        "group_abbr": "cpu",
                        "vals": ["m2", "m3"],
                    },
                    "inches": {
                        "group_name": "Диагональ",
                        "group_abbr": "inches",
                        "vals": ["13", "15"],
                    },
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": ["256", "512"],
                    },
                    "ram": {
                        "group_name": "Оперативная память",
                        "group_abbr": "ram",
                        "vals": ["8", "16"],
                    },
                    "is_retina": {
                        "group_name": "Дисплей Retina",
                        "group_abbr": "is_retina",
                        "vals": [
                            {"name": "Retina", "abbr": True},
                            {"name": "Не Retina", "abbr": False},
                        ],
                    },
                },
            },
            "macbookpro": {
                "device_abbr": "macbookpro",
                "device_name": "MacBook Pro",
                "seq_position": 10,
                "params": {
                    "year": {
                        "group_name": "Год",
                        "group_abbr": "year",
                        "vals": [2017, 2018, 2019, 2020, 2022, 2023, 2024],
                    },
                    "cpu": {
                        "group_name": "Процессор",
                        "group_abbr": "cpu",
                        "vals": ["m4", "m3"],
                    },
                    "inches": {
                        "group_name": "Диагональ",
                        "group_abbr": "inches",
                        "vals": ["14", "16"],
                    },
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": ["512", "1024"],
                    },
                    "ram": {
                        "group_name": "Оперативная память",
                        "group_abbr": "ram",
                        "vals": ["18", "36"],
                    },
                    "is_retina": {
                        "group_name": "Дисплей Retina",
                        "group_abbr": "is_retina",
                        "vals": [
                            {"name": "Retina", "abbr": True},
                            {"name": "Не Retina", "abbr": False},
                        ],
                    },
                },
            }
        },
        "https://damprodam.ru/py/android_buyout/params": [
            {
                "device_abbr": "galaxy_s25",
                "device_name": "Galaxy S25",
                "seq_position": 2,
                "params": {
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": [
                            {"name": "128 ГБ", "abbr": "128"},
                            {"name": "256 ГБ", "abbr": "256"},
                        ],
                    }
                },
            },
            {
                "device_abbr": "galaxy_s24",
                "device_name": "Galaxy S24",
                "seq_position": 1,
                "params": {
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": [
                            {"name": "128 ГБ", "abbr": "128"},
                        ],
                    }
                },
            },
        ],
        "https://damprodam.ru/py/ipad_buyout/params": {
            "ipad_air": {
                "device_abbr": "ipad_air",
                "device_name": "iPad Air",
                "seq_position": 1,
                "params": {
                    "memory": {
                        "group_name": "Объем накопителя",
                        "group_abbr": "memory",
                        "vals": [
                            {"name": "128 ГБ", "abbr": "128"},
                        ],
                    },
                    "cellular": {
                        "group_name": "Cellular",
                        "group_abbr": "cellular",
                        "vals": [
                            {"name": "Wifi", "abbr": "0"},
                            {"name": "Wifi + Cellular", "abbr": "1"},
                        ],
                    },
                },
            }
        },
        "https://damprodam.ru/py/watches_buyout/params": [
            {
                "device_abbr": "aws10",
                "device_name": "Series 10",
                "seq_position": 1,
                "params": {
                    "size_mm": {
                        "group_name": "Миллиметры",
                        "group_abbr": "size_mm",
                        "vals": [
                            {"name": "42мм", "abbr": "42", "price_scratch": 6000},
                        ],
                    }
                },
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payloads[str(request.url)])

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://damprodam.ru/py/")
    api_client = DamProdamApiClient(http_client, base_url="https://damprodam.ru/py/")
    importer = DamProdamSnapshotImporter(api_client)

    snapshot = await importer.import_snapshot()
    await http_client.aclose()

    assert snapshot.pricing_city == "moscow"
    assert {category.category_code for category in snapshot.categories} == set(SupportedCategory)

    samsung_category = next(
        category
        for category in snapshot.categories
        if category.category_code is SupportedCategory.SAMSUNG
    )
    samsung_memory = next(
        question for question in samsung_category.questions if question.code == "memory"
    )
    assert samsung_memory.branching_rules["model_option_map"] == {
        "galaxy_s25": ["128", "256"],
        "galaxy_s24": ["128"],
    }

    watch_category = next(
        category
        for category in snapshot.categories
        if category.category_code is SupportedCategory.APPLE_WATCH
    )
    watch_condition = next(
        question for question in watch_category.questions if question.code == "exterier_condition_watches"
    )
    assert [option.code for option in watch_condition.options] == ["best", "normal", "scratch"]

    watch_size = next(
        question for question in watch_category.questions if question.code == "size_mm"
    )
    assert watch_size.options[0].pricing_payload == {"price_scratch": 6000}

    mac_category = next(
        category
        for category in snapshot.categories
        if category.category_code is SupportedCategory.MAC
    )
    assert [question.code for question in mac_category.questions[:5]] == [
        "year",
        "cpu",
        "inches",
        "memory",
        "ram",
    ]
    year_question = next(
        question for question in mac_category.questions if question.code == "year"
    )
    assert [option.code for option in year_question.options] == [
        "2015",
        "2016",
        "2017",
        "2018",
        "2019",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]
    retina_question = next(
        question for question in mac_category.questions if question.code == "is_retina"
    )
    assert [option.code for option in retina_question.options] == ["true", "false"]

    iphone_category = next(
        category
        for category in snapshot.categories
        if category.category_code is SupportedCategory.IPHONE
    )
    iphone_required = {
        question.code
        for question in iphone_category.questions
    }
    assert {"damaged", "restored_display", "exterier_condition"}.issubset(iphone_required)


class StubMacEnrichmentApiClient:
    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: dict[str, str] | None = None,
    ) -> dict[str, dict]:
        assert category is SupportedCategory.MAC
        if not payload:
            return {
                "macbookpro": {
                    "device_abbr": "macbookpro",
                    "device_name": "MacBook Pro",
                    "seq_position": 1,
                    "params": {
                        "year": {
                            "group_name": "Год",
                            "group_abbr": "year",
                            "vals": [2023],
                        },
                        "cpu": {
                            "group_name": "Процессор",
                            "group_abbr": "cpu",
                            "vals": [],
                        },
                    },
                }
            }

        return {
            "macbookpro": {
                "params": {
                    "cpu": {
                        "group_name": "Процессор",
                        "group_abbr": "cpu",
                        "vals": [
                            {"name": "Apple M3", "abbr": "applem3"},
                            {"name": "Apple M3 Pro", "abbr": "applem3pro"},
                        ],
                    },
                    "inches": {
                        "group_name": "Диагональ",
                        "group_abbr": "inches",
                        "vals": [
                            {"name": "14", "abbr": "14"},
                            {"name": "16", "abbr": "16"},
                        ],
                    },
                }
            }
        }


async def test_importer_enriches_mac_dependent_questions_from_year_params() -> None:
    importer = DamProdamSnapshotImporter(StubMacEnrichmentApiClient())

    category = await importer._build_category_schema(
        SupportedCategory.MAC,
        await importer._api_client.fetch_category_params(SupportedCategory.MAC),
        sort_order=0,
    )

    cpu_question = next(question for question in category.questions if question.code == "cpu")
    assert [option.code for option in cpu_question.options] == ["applem3", "applem3pro"]