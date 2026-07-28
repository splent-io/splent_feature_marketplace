from splent_framework.fixtures.fixtures import *  # noqa: F401,F403

import copy

import pytest

import splent_io.splent_feature_marketplace.services as marketplace_services

# A miniature but structurally faithful marketplace index (same shape as the
# document produced by `splent marketplace:index`).
SAMPLE_INDEX = {
    "schema": 1,
    "generated_at": "2026-07-26T00:00:00+00:00",
    "generator": "splent_cli/test",
    "features": [
        {
            "id": "splent-io/splent_feature_events",
            "org": "splent-io",
            "repo": "splent_feature_events",
            "short": "events",
            "version": None,
            "project_version": "1.2.0",
            "description": "Talks, workshops and competitions for the campus",
            "archetype": "full",
            "category": "content",
            "tags": ["calendar"],
            "env": None,
            "provides": {
                "routes": ["/events", "/events/<slug>"],
                "blueprints": ["events_bp"],
                "models": ["Event"],
                "commands": [],
                "hooks": ["layout.authenticated_sidebar"],
                "services": ["EventsService"],
                "signals": [],
                "translations": ["en", "es"],
                "docker": [],
            },
            "requires": {"features": [], "env_vars": [], "signals": []},
            "extensible": {
                "services": ["EventsService"],
                "templates": [],
                "models": ["Event"],
                "hooks": [],
                "routes": False,
            },
            "refinement": None,
            "requires_python": ">=3.13",
            "source": "workspace",
            "used_by": ["public"],
            "pypi": {"published": True, "latest": "1.2.0", "has_current": True},
            "github": "https://github.com/splent-io/splent_feature_events",
        },
        {
            "id": "splent-io/splent_feature_mail",
            "org": "splent-io",
            "repo": "splent_feature_mail",
            "short": "mail",
            "version": None,
            "project_version": "0.9.0",
            "description": "Transactional email over SMTP",
            "archetype": "service",
            "category": "infrastructure",
            "tags": ["smtp", "email"],
            "env": None,
            "provides": {
                "routes": [],
                "blueprints": [],
                "models": [],
                "commands": [],
                "hooks": [],
                "services": ["MailService"],
                "signals": [],
                "translations": [],
                "docker": [],
            },
            "requires": {
                "features": ["auth"],
                "features_optional": ["settings"],
                "env_vars": ["MAIL_HOST"],
                "signals": [],
            },
            "extensible": {
                "services": ["MailService"],
                "templates": [],
                "models": [],
                "hooks": [],
                "routes": False,
            },
            "refinement": None,
            "requires_python": ">=3.13",
            "source": "workspace",
            "used_by": ["contact"],
            "pypi": None,
            "github": None,
        },
        {
            "id": "splent-io/splent_feature_theme",
            "org": "splent-io",
            "repo": "splent_feature_theme",
            "short": "theme",
            "version": None,
            "project_version": "2.0.0",
            "description": "Public shell with tokens and skins",
            "archetype": "light",
            "category": "content",
            "tags": [],
            "env": None,
            "provides": {
                "routes": ["/theme"],
                "blueprints": ["theme_bp"],
                "models": [],
                "commands": [],
                "hooks": [],
                "services": [],
                "signals": [],
                "translations": [],
                "docker": [],
            },
            "requires": {"features": [], "env_vars": [], "signals": []},
            "extensible": {
                "services": [],
                "templates": [],
                "models": [],
                "hooks": [],
                "routes": False,
            },
            "refinement": None,
            "requires_python": ">=3.13",
            "source": "workspace",
            "used_by": [],
            "pypi": None,
            "github": None,
        },
    ],
    "spls": [
        {
            "name": "cms_spl",
            "description": "CMS SPL for content-driven sites",
            "uvl": {"mirror": "uvlhub.io", "doi": "", "file": "cms_spl.uvl"},
            "model": {
                "features": {
                    "theme": {
                        "org": "splent-io",
                        "package": "splent_feature_theme",
                        "presence": "mandatory",
                        "group": None,
                        "group_kind": None,
                    },
                    "events": {
                        "org": "splent-io",
                        "package": "splent_feature_events",
                        "presence": "optional",
                        "group": None,
                        "group_kind": None,
                    },
                    "session_filesystem": {
                        "org": "splent-io",
                        "package": "splent_feature_session_filesystem",
                        "presence": "mandatory",
                        "group": "session",
                        "group_kind": "alternative",
                    },
                    "session_redis": {
                        "org": "splent-io",
                        "package": "splent_feature_session_redis",
                        "presence": "mandatory",
                        "group": "session",
                        "group_kind": "alternative",
                    },
                }
            },
        }
    ],
    "collisions": [
        {"kind": "route", "item": "/events", "features": ["events", "calendar"]},
        {
            "kind": "service",
            "item": "CaptchaService",
            "features": ["cloudflare", "recaptcha"],
        },
    ],
}


@pytest.fixture(autouse=True)
def reset_marketplace_cache():
    """Keep the module-level TTL cache isolated between tests."""

    def _reset():
        marketplace_services._cache.update({"index": None, "fetched_at": 0.0})
        marketplace_services._cache.pop("es_indexed_for", None)

    _reset()
    yield
    _reset()


@pytest.fixture()
def sample_index():
    return copy.deepcopy(SAMPLE_INDEX)


@pytest.fixture()
def stub_index(monkeypatch, sample_index):
    """Patch MarketplaceService to serve the sample index (no network, no disk)."""
    monkeypatch.setattr(
        marketplace_services.MarketplaceService,
        "_load_index",
        lambda self, force=False: sample_index,
    )
    return sample_index
