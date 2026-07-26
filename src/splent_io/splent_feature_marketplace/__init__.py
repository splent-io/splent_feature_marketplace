from splent_framework.blueprints.base_blueprint import create_blueprint
from splent_framework.nav.nav_registry import register_nav_item
from splent_framework.services.service_locator import register_service

from splent_io.splent_feature_marketplace.services import MarketplaceService

marketplace_bp = create_blueprint(__name__)


def init_feature(app):
    register_service(app, "MarketplaceService", MarketplaceService)
    # Public storefront navigation: composed per-derivation by the theme from
    # the installed features (see splent_framework.nav.nav_registry).
    register_nav_item(
        key="marketplace", label="Marketplace", href="/marketplace", order=10
    )
    register_nav_item(
        key="marketplace_spls",
        label="Product lines",
        href="/marketplace/spls",
        order=20,
    )
    register_nav_item(
        key="marketplace_publish",
        label="Publish",
        href="/marketplace/publish",
        order=30,
    )


def inject_context_vars(app):
    return {}
