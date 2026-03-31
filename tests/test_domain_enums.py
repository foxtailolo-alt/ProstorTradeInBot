from src.domain.enums import SupportedCategory
from src.storage.models.snapshot import SUPPORTED_CATEGORY_CODES


def test_supported_categories_match_project_scope() -> None:
    assert SUPPORTED_CATEGORY_CODES == {item.value for item in SupportedCategory}
    assert SUPPORTED_CATEGORY_CODES == {
        "iphone",
        "mac",
        "samsung",
        "ipad",
        "apple_watch",
    }
