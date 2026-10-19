from app.core.templates import _google_maps_api_key_for_host, is_local_development_host


def test_local_development_host_detection():
    assert is_local_development_host("localhost")
    assert is_local_development_host("127.0.0.1")
    assert is_local_development_host("dev.localhost")
    assert not is_local_development_host("occaserve.com")


def test_localhost_uses_local_maps_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "production-key")
    monkeypatch.setenv("GOOGLE_MAPS_LOCAL_API_KEY", "local-key")

    assert _google_maps_api_key_for_host("localhost") == "local-key"
    assert _google_maps_api_key_for_host("127.0.0.1") == "local-key"
    assert _google_maps_api_key_for_host("dev.localhost") == "local-key"


def test_non_local_hosts_use_production_maps_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "production-key")
    monkeypatch.setenv("GOOGLE_MAPS_LOCAL_API_KEY", "local-key")

    assert _google_maps_api_key_for_host("occaserve.com") == "production-key"


def test_maps_key_is_empty_when_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_LOCAL_API_KEY", raising=False)

    assert _google_maps_api_key_for_host("localhost") == ""
    assert _google_maps_api_key_for_host("occaserve.com") == ""
