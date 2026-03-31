from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AppHealth:
    bot_enabled: bool
    pricing_city: str
    environment: str
