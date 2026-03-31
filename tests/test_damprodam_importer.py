from __future__ import annotations

import httpx

from src.domain.enums import SupportedCategory
from src.parser.damprodam import DamProdamApiClient, DamProdamSnapshotImporter


async def test_importer_builds_snapshot_from_api_payloads() -> None:
    payloads = {
        "/py/iphone_buyout/params": [
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
        "/py/macbook_buyout/params": {
            "macbookair": {
                "device_abbr": "macbookair",
                "device_name": "MacBook Air",
                "seq_position": 1,
                "params": {
                    "year": {
                        "group_name": "Год",
                        "group_abbr": "year",
                        "vals": [2022, 2023],
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
        "/py/android_buyout/params": [
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
        "/py/ipad_buyout/params": {
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
        "/py/watches_buyout/params": [
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
    http_client = httpx.AsyncClient(transport=transport)
    api_client = DamProdamApiClient(http_client, base_url="https://damprodam.ru/py/")
    importer = DamProdamSnapshotImporter(api_client)

    snapshot = await importer.import_snapshot()
    await http_client.aclose()

    assert snapshot.pricing_city == "moscow"
    assert {category.category_code for category in snapshot.categories} == set(SupportedCategory)

    samsung_category = next(category for category in snapshot.categories if category.category_code is SupportedCategory.SAMSUNG)
    samsung_memory = next(question for question in samsung_category.questions if question.code == "memory")
    assert samsung_memory.branching_rules["model_option_map"] == {
        "galaxy_s25": ["128", "256"],
        "galaxy_s24": ["128"],
    }

    watch_category = next(category for category in snapshot.categories if category.category_code is SupportedCategory.APPLE_WATCH)
    watch_size = next(question for question in watch_category.questions if question.code == "size_mm")
    assert watch_size.options[0].pricing_payload == {"price_scratch": 6000}

    mac_category = next(category for category in snapshot.categories if category.category_code is SupportedCategory.MAC)
    retina_question = next(question for question in mac_category.questions if question.code == "is_retina")
    assert [option.code for option in retina_question.options] == ["True", "False"]