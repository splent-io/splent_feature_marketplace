"""
Which index wins, and why it matters.

The rule used to be "a local workspace cache means a development checkout,
so local is the truth". That is right on a laptop and wrong on a server
that runs from a workspace: it then serves a local copy that never expires,
so a freshly published feature or product line never appears. The goal is
the plain one, that a developer publishes something and the marketplace in
production shows it, so the more recently generated index wins.
"""

from splent_io.splent_feature_marketplace.services import MarketplaceService


def _index(generated_at, name):
    return {
        "schema": 1,
        "generated_at": generated_at,
        "features": [{"short": name}],
        "spls": [{"name": name}],
    }


def test_the_newer_remote_wins_over_a_stale_local_copy():
    """The regression: a server whose local copy predates the published one."""
    local = _index("2026-07-29T17:29:10+00:00", "stale")
    remote = _index("2026-07-29T23:06:32+00:00", "fresh")
    assert MarketplaceService._newer_index(local, remote) is remote


def test_a_developers_fresh_build_wins_over_the_published_one():
    """Someone who just ran marketplace:index is looking at their own work."""
    local = _index("2026-07-30T09:00:00+00:00", "mine")
    remote = _index("2026-07-29T23:06:32+00:00", "published")
    assert MarketplaceService._newer_index(local, remote) is local


def test_local_is_used_when_the_network_is_down():
    local = _index("2026-07-29T17:29:10+00:00", "local")
    assert MarketplaceService._newer_index(local, None) is local


def test_remote_is_used_when_there_is_no_local_copy():
    """The shape of a production container built from an image."""
    remote = _index("2026-07-29T23:06:32+00:00", "remote")
    assert MarketplaceService._newer_index(None, remote) is remote


def test_neither_source_yields_nothing():
    assert MarketplaceService._newer_index(None, None) is None


def test_a_tie_goes_to_the_published_index():
    """It is the shared answer, so it is the better default."""
    same = "2026-07-29T23:06:32+00:00"
    local, remote = _index(same, "local"), _index(same, "remote")
    assert MarketplaceService._newer_index(local, remote) is remote


def test_an_index_without_a_timestamp_loses_to_one_that_has_it():
    undated = {"schema": 1, "features": [], "spls": []}
    dated = _index("2026-07-29T23:06:32+00:00", "dated")
    assert MarketplaceService._newer_index(undated, dated) is dated
    assert MarketplaceService._newer_index(dated, undated) is dated


def test_a_malformed_source_is_treated_as_absent():
    """Both sources are untrusted: a URL that may be down and a local file
    anyone can edit."""
    service = MarketplaceService()

    def broken():
        raise OSError("no such file")

    def wrong_shape():
        return {"not": "an index"}

    assert service._read_valid(broken) is None
    assert service._read_valid(wrong_shape) is None
    assert service._read_valid(lambda: _index("2026-01-01T00:00:00+00:00", "ok"))
