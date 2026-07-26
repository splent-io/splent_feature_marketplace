"""
Unit tests for splent_feature_marketplace.

MarketplaceService is exercised in isolation: the remote index fetch and the
local workspace cache are mocked, so no network or disk state is touched.
"""

import json
import types
from unittest.mock import MagicMock
from urllib.error import URLError

import pytest

import splent_io.splent_feature_marketplace.services as services
from splent_io.splent_feature_marketplace.services import MarketplaceService


@pytest.fixture()
def remote_index(monkeypatch, sample_index):
    """Serve the sample index through the remote fetch path."""
    monkeypatch.setattr(
        MarketplaceService, "_fetch_remote", lambda self: sample_index
    )
    return sample_index


@pytest.fixture()
def network_down(monkeypatch):
    monkeypatch.setattr(
        MarketplaceService,
        "_fetch_remote",
        MagicMock(side_effect=URLError("network down")),
    )


# ── queries ───────────────────────────────────────────────────────────────


def test_all_features_sorted_by_short(remote_index):
    shorts = [f["short"] for f in MarketplaceService().all_features()]
    assert shorts == ["events", "mail", "theme"]


def test_find_by_short(remote_index):
    feature = MarketplaceService().find("events")
    assert feature is not None
    assert feature["id"] == "splent-io/splent_feature_events"


def test_find_by_repo_name(remote_index):
    feature = MarketplaceService().find("splent_feature_mail")
    assert feature is not None
    assert feature["short"] == "mail"


def test_find_missing_returns_none(remote_index):
    assert MarketplaceService().find("does_not_exist") is None


def test_search_query_matches_description_case_insensitive(remote_index):
    results = MarketplaceService().search(query="SMTP")
    assert [f["short"] for f in results] == ["mail"]


def test_search_query_matches_tags(remote_index):
    results = MarketplaceService().search(query="calendar")
    assert [f["short"] for f in results] == ["events"]


def test_search_filters_by_archetype(remote_index):
    results = MarketplaceService().search(archetype="light")
    assert [f["short"] for f in results] == ["theme"]


def test_search_filters_by_category(remote_index):
    results = MarketplaceService().search(category="content")
    assert [f["short"] for f in results] == ["events", "theme"]


def test_search_combines_query_and_category(remote_index):
    results = MarketplaceService().search(query="skins", category="content")
    assert [f["short"] for f in results] == ["theme"]


def test_spls_and_collisions(remote_index):
    service = MarketplaceService()
    assert [s["name"] for s in service.spls()] == ["cms_spl"]
    assert len(service.collisions()) == 2


def test_collisions_for_feature(remote_index):
    collisions = MarketplaceService().collisions_for("events")
    assert len(collisions) == 1
    assert collisions[0]["item"] == "/events"


def test_archetype_and_category_facets(remote_index):
    service = MarketplaceService()
    assert service.archetypes() == ["full", "light", "service"]
    assert service.categories() == ["content", "infrastructure"]


# ── caching & fallback ────────────────────────────────────────────────────


def test_remote_fetched_once_within_ttl(monkeypatch, sample_index):
    fetch = MagicMock(return_value=sample_index)
    monkeypatch.setattr(MarketplaceService, "_fetch_remote", fetch)
    service = MarketplaceService()
    service.all_features()
    service.find("events")
    service.spls()
    assert fetch.call_count == 1


def test_cache_expires_after_ttl(monkeypatch, sample_index):
    fetch = MagicMock(return_value=sample_index)
    monkeypatch.setattr(MarketplaceService, "_fetch_remote", fetch)

    now = [1000.0]
    monkeypatch.setattr(services, "time", types.SimpleNamespace(time=lambda: now[0]))

    service = MarketplaceService()
    service.all_features()
    now[0] += services.CACHE_TTL_SECONDS + 1
    service.all_features()
    assert fetch.call_count == 2


def test_network_failure_falls_back_to_local_cache(
    network_down, monkeypatch, sample_index, tmp_path
):
    local = tmp_path / "index.json"
    local.write_text(json.dumps(sample_index), encoding="utf-8")
    monkeypatch.setattr(
        MarketplaceService, "_local_cache_path", lambda self: str(local)
    )

    features = MarketplaceService().all_features()
    assert [f["short"] for f in features] == ["events", "mail", "theme"]


def test_no_network_and_no_local_cache_yields_empty_index(
    network_down, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        MarketplaceService,
        "_local_cache_path",
        lambda self: str(tmp_path / "missing.json"),
    )

    service = MarketplaceService()
    assert service.all_features() == []
    assert service.spls() == []
    assert service.collisions() == []


def test_stale_memory_copy_served_when_everything_fails(
    monkeypatch, sample_index, tmp_path
):
    fetch = MagicMock(side_effect=[sample_index, URLError("down")])
    monkeypatch.setattr(MarketplaceService, "_fetch_remote", fetch)
    monkeypatch.setattr(
        MarketplaceService,
        "_local_cache_path",
        lambda self: str(tmp_path / "missing.json"),
    )

    now = [1000.0]
    monkeypatch.setattr(services, "time", types.SimpleNamespace(time=lambda: now[0]))

    service = MarketplaceService()
    assert len(service.all_features()) == 3

    # TTL expires, refresh fails, no local file: the stale copy is kept.
    now[0] += services.CACHE_TTL_SECONDS + 1
    assert len(service.all_features()) == 3
    assert fetch.call_count == 2
