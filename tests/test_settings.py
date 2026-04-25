from decimal import Decimal

from app.services.settings_service import SettingsService


class DummyRepo:
    def __init__(self):
        self.values = {"enabled": "true", "count": "7", "amount": "12.50"}

    def get_value(self, key):
        return self.values.get(key)

    def set_value(self, key, value, value_type=None):
        self.values[key] = value

    def all_settings(self):
        return self.values


def test_settings_typed_helpers_without_database():
    service = SettingsService.__new__(SettingsService)
    service.repo = DummyRepo()
    assert service.get_bool("enabled") is True
    assert service.get_int("count") == 7
    assert service.get_decimal("amount") == Decimal("12.50")

