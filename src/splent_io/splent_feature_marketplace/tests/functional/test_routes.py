"""
Functional tests for splent_feature_marketplace.

Functional tests use Flask's test client to exercise full HTTP
request/response cycles. The MarketplaceService index is patched with the
sample index (see tests/conftest.py) so no network access happens.
"""


def _html(response):
    return response.data.decode("utf-8")


# ── GET /marketplace ──────────────────────────────────────────────────────


def test_index_lists_all_features(test_client, stub_index):
    response = test_client.get("/marketplace")
    assert response.status_code == 200
    html = _html(response)
    assert 'href="/marketplace/events"' in html
    assert 'href="/marketplace/mail"' in html
    assert 'href="/marketplace/theme"' in html
    assert "Talks, workshops and competitions for the campus" in html


def test_index_filters_by_query(test_client, stub_index):
    response = test_client.get("/marketplace?q=smtp")
    assert response.status_code == 200
    html = _html(response)
    assert 'href="/marketplace/mail"' in html
    assert 'href="/marketplace/events"' not in html


def test_index_filters_by_archetype(test_client, stub_index):
    response = test_client.get("/marketplace?archetype=light")
    assert response.status_code == 200
    html = _html(response)
    assert 'href="/marketplace/theme"' in html
    assert 'href="/marketplace/events"' not in html
    assert 'href="/marketplace/mail"' not in html


def test_index_filters_by_category(test_client, stub_index):
    response = test_client.get("/marketplace?category=infrastructure")
    assert response.status_code == 200
    html = _html(response)
    assert 'href="/marketplace/mail"' in html
    assert 'href="/marketplace/theme"' not in html


# ── GET /marketplace/<short> ──────────────────────────────────────────────


def test_detail_shows_contract_and_install_command(test_client, stub_index):
    response = test_client.get("/marketplace/events")
    assert response.status_code == 200
    html = _html(response)
    assert "splent feature:install splent-io/splent_feature_events" in html
    assert "EventsService" in html
    assert "Event" in html
    assert "/events/&lt;slug&gt;" in html or "/events/<slug>" in html
    # Published on PyPI and linked to its repository.
    assert "https://github.com/splent-io/splent_feature_events" in html


def test_detail_shows_dependencies_and_used_by(test_client, stub_index):
    response = test_client.get("/marketplace/mail")
    assert response.status_code == 200
    html = _html(response)
    # Hard dependency, soft dependency ("works better with") and used_by chips.
    assert 'href="/marketplace/auth"' in html
    assert 'href="/marketplace/settings"' in html
    assert 'href="/marketplace/contact"' in html
    assert "MAIL_HOST" in html


def test_detail_unknown_short_returns_404(test_client, stub_index):
    response = test_client.get("/marketplace/does_not_exist")
    assert response.status_code == 404


def test_detail_tolerates_feature_without_contract_keys(
    test_client, sample_index, monkeypatch
):
    """An index entry without provides/requires/tags/used_by (the index is
    remote, unvalidated JSON) must render a degraded sheet, never a 500."""
    import splent_io.splent_feature_marketplace.services as services

    events = sample_index["features"][0]
    for key in ("provides", "requires", "tags", "used_by"):
        events.pop(key, None)
    # Serve through the real _load_index so normalization kicks in.
    monkeypatch.setattr(
        services.MarketplaceService, "_read_local", lambda self: sample_index
    )

    response = test_client.get("/marketplace/events")
    assert response.status_code == 200
    html = _html(response)
    assert "This feature declares no public contract surface." in html
    assert "No hard dependencies." in html

    # The grid also renders fine with the degraded entry.
    assert test_client.get("/marketplace").status_code == 200


# ── GET /marketplace/spls ─────────────────────────────────────────────────


def test_spls_page_shows_groups_and_features(test_client, stub_index):
    response = test_client.get("/marketplace/spls")
    assert response.status_code == 200
    html = _html(response)
    assert "cms_spl" in html
    # Collapsible blocks with counts replaced the uvl filename badge.
    assert "store-fold" in html
    assert "Always included" in html
    # Features published in the index link to their detail page.
    assert 'href="/marketplace/theme"' in html
    assert 'href="/marketplace/events"' in html
    # Model features absent from the index (only referenced by the SPL, e.g.
    # published on GitHub/PyPI but not indexed) render as unlinked chips
    # marked "external" instead of pointing to a 404.
    assert 'href="/marketplace/session_filesystem"' not in html
    assert 'href="/marketplace/session_redis"' not in html
    assert "session_filesystem" in html
    assert "session_redis" in html
    assert "store-chip-link--external" in html


# ── GET /marketplace/publish ──────────────────────────────────────────────


def test_publish_page_explains_the_release_and_registry_flow(test_client, stub_index):
    response = test_client.get("/marketplace/publish")
    assert response.status_code == 200
    html = _html(response)
    assert "Publish your feature" in html
    # The three mechanics: release command, registry PR, no upload API.
    assert "splent feature:release" in html
    assert "splent-io/splent_index" in html
    assert "https://docs.splent.io/marketplace/publishing" in html


def test_publish_is_not_swallowed_by_the_detail_route(test_client, stub_index):
    # /marketplace/<short> would 404 on an unknown short; the static rule
    # must win over the converter rule for "publish".
    response = test_client.get("/marketplace/publish")
    assert response.status_code == 200
    assert "Publish your feature" in _html(response)


# ── distribution state, git tag and PyPI are independent ──────────────────


def _detail(test_client, short):
    response = test_client.get(f"/marketplace/{short}")
    assert response.status_code == 200
    return _html(response)


def test_a_feature_on_pypi_shows_its_published_version(test_client, stub_index):
    html = _detail(test_client, "events")
    assert "v1.2.0" in html
    assert "Not published" not in html


def test_a_feature_without_pypi_says_so(test_client, stub_index):
    """The regression: pypi is a dict, and {'published': false} is truthy, so
    every feature claimed to be on PyPI."""
    html = _detail(test_client, "mail")
    assert "Not published" in html
    assert "A production build resolves features from PyPI" in html


def test_a_released_but_unpublished_feature_is_not_claimed_as_published(
    test_client, monkeypatch, sample_index
):
    from splent_io.splent_feature_marketplace.services import MarketplaceService

    degraded = dict(sample_index)
    degraded["features"] = [
        dict(
            f,
            pypi={"published": False, "latest": None, "has_current": False},
        )
        for f in sample_index["features"]
    ]
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: degraded)

    html = _detail(test_client, "events")
    assert "Not published" in html

    grid = _html(test_client.get("/marketplace"))
    assert "source only" in grid


def test_pypi_behind_the_tag_is_flagged(test_client, monkeypatch, sample_index):
    from splent_io.splent_feature_marketplace.services import MarketplaceService

    behind = dict(sample_index)
    behind["features"] = [
        dict(f, pypi={"published": True, "latest": "0.9.0", "has_current": False})
        if f["short"] == "events"
        else f
        for f in sample_index["features"]
    ]
    monkeypatch.setattr(MarketplaceService, "_read_local", lambda self: behind)

    html = _detail(test_client, "events")
    assert "behind" in html
    assert "0.9.0" in html
