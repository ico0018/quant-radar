from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.bitget_rest_url == "https://api.bitget.com"
    assert settings.bitget_ws_url == "wss://ws.bitget.com/v2/ws/public"


def test_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("BITGET_REST_URL", "https://market.example.test")
    get_settings.cache_clear()
    assert get_settings().bitget_rest_url == "https://market.example.test"
    get_settings.cache_clear()
