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



@pytest.fixture(autouse=True)
def _no_local_cache(monkeypatch):
    """Index resolution is local-first; unit tests must not see the real
    workspace cache. Tests exercising the local path re-patch _read_local."""

    def _raise(self):
        raise OSError("no local cache in unit tests")

    monkeypatch.setattr(MarketplaceService, "_read_local", _raise)


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


def test_local_cache_is_preferred_over_remote(
    network_down, monkeypatch, sample_index
):
    # Local-first: a readable workspace cache is served without ever touching
    # the network (network_down would make any remote attempt blow up).
    monkeypatch.setattr(
        MarketplaceService, "_read_local", lambda self: sample_index
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


@pytest.mark.parametrize(
    "bad_payload",
    [
        [],  # valid JSON, wrong top-level type
        {"features": "oops"},  # dict without schema, features not a list
        {"schema": 1, "features": "oops"},  # right schema, wrong field shape
    ],
)
def test_malformed_local_cache_falls_back_to_remote(
    remote_index, monkeypatch, bad_payload
):
    """Valid-JSON-but-wrong-shape local caches are treated as missing."""
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: bad_payload)
    features = MarketplaceService().all_features()
    assert [f["short"] for f in features] == ["events", "mail", "theme"]


def test_malformed_remote_index_yields_empty_index(network_down, monkeypatch):
    monkeypatch.setattr(
        MarketplaceService, "_read_local", lambda self: {"features": "oops"}
    )
    service = MarketplaceService()
    assert service.all_features() == []
    assert service.spls() == []
    assert service.collisions() == []


def test_malformed_index_never_poisons_the_ttl_cache(monkeypatch, sample_index):
    """A wrong-shape document must not be stored: routes recover as soon as
    the source is fixed, instead of 500ing for CACHE_TTL_SECONDS."""
    monkeypatch.setattr(
        MarketplaceService,
        "_fetch_remote",
        MagicMock(side_effect=URLError("network down")),
    )
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: [])
    service = MarketplaceService()
    assert service.all_features() == []
    assert services._cache["index"] is None  # the bad value was never cached

    # The local cache is fixed: the very next call (well within the TTL)
    # serves it instead of a poisoned in-memory copy.
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: sample_index)
    assert [f["short"] for f in service.all_features()] == [
        "events",
        "mail",
        "theme",
    ]


def test_non_dict_entries_are_dropped_and_feature_keys_defaulted(monkeypatch):
    degraded = {
        "schema": 1,
        "features": [
            {"short": "bare", "repo": "splent_feature_bare"},  # no provides/requires
            "not-a-feature",
        ],
        "spls": ["not-an-spl"],
        "collisions": [
            "bad-entry",
            {"kind": "route", "item": "/x", "features": ["bare"]},
        ],
    }
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: degraded)
    service = MarketplaceService()

    feature = service.find("bare")
    assert feature["provides"] == {}
    assert feature["requires"] == {}
    assert feature["tags"] == []
    assert feature["used_by"] == []

    assert service.spls() == []
    assert service.collisions_for("bare") == [
        {"kind": "route", "item": "/x", "features": ["bare"]}
    ]


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


# ── optional Elasticsearch upgrade ────────────────────────────────────────


class _FakeES:
    def __init__(self, shorts):
        self.shorts = shorts
        self.indexed = []
        self.refreshed = []

    def available(self):
        return True

    def ensure_index(self, name, mappings=None):
        return True

    def index_document(self, index, doc_id, body):
        self.indexed.append(doc_id)

    def refresh_index(self, name):
        self.refreshed.append(name)

    def search(self, index, query_body):
        return {"hits": [{"_source": {"short": s}} for s in self.shorts]}


class _LegacyES(_FakeES):
    """An ElasticsearchService predating refresh_index support."""

    refresh_index = None


def test_search_uses_elasticsearch_ranking_when_available(remote_index, monkeypatch):
    fake = _FakeES(["mail", "events"])
    monkeypatch.setattr(MarketplaceService, "_es_service", lambda self: fake)
    results = MarketplaceService().search(query="anything")
    assert [f["short"] for f in results] == ["mail", "events"]
    assert set(fake.indexed) == {"events", "mail", "theme"}


def test_es_index_is_refreshed_after_indexing(remote_index, monkeypatch):
    """ES is near-real-time: without a refresh, a fresh index answers [] for
    the search that follows the indexing loop in the same request."""
    fake = _FakeES(["events"])
    monkeypatch.setattr(MarketplaceService, "_es_service", lambda self: fake)
    MarketplaceService().search(query="events")
    assert fake.refreshed == [MarketplaceService.ES_INDEX_NAME]


def test_es_without_refresh_support_still_ranks(remote_index, monkeypatch):
    fake = _LegacyES(["mail", "events"])
    monkeypatch.setattr(MarketplaceService, "_es_service", lambda self: fake)
    results = MarketplaceService().search(query="anything")
    assert [f["short"] for f in results] == ["mail", "events"]


def test_search_falls_back_in_memory_without_elasticsearch(remote_index, monkeypatch):
    monkeypatch.setattr(MarketplaceService, "_es_service", lambda self: None)
    results = MarketplaceService().search(query="SMTP")
    assert [f["short"] for f in results] == ["mail"]


def test_search_falls_back_when_elasticsearch_errors(remote_index, monkeypatch):
    class _BrokenES(_FakeES):
        def search(self, index, query_body):
            raise RuntimeError("es down mid-flight")

    monkeypatch.setattr(
        MarketplaceService, "_es_service", lambda self: _BrokenES([])
    )
    results = MarketplaceService().search(query="SMTP")
    assert [f["short"] for f in results] == ["mail"]
