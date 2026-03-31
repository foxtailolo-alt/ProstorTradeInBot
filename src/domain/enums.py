from enum import StrEnum


class SupportedCategory(StrEnum):
    IPHONE = "iphone"
    MAC = "mac"
    SAMSUNG = "samsung"
    IPAD = "ipad"
    APPLE_WATCH = "apple_watch"


class SnapshotStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
