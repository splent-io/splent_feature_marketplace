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


# ── GET /marketplace/spls ─────────────────────────────────────────────────


def test_spls_page_shows_groups_and_features(test_client, stub_index):
    response = test_client.get("/marketplace/spls")
    assert response.status_code == 200
    html = _html(response)
    assert "cms_spl" in html
    assert "cms_spl.uvl" in html
    # Mandatory, optional and the alternative "session" group.
    assert 'href="/marketplace/theme"' in html
    assert 'href="/marketplace/events"' in html
    assert 'href="/marketplace/session_filesystem"' in html
    assert 'href="/marketplace/session_redis"' in html
