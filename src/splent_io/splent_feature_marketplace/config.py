"""marketplace feature configuration.

Exposes the SPLENT index location so products can point the catalog at a
different index (e.g. a private org index) via their .env.

To regenerate from source code: splent feature:inject-config splent_feature_marketplace
"""

import os

from splent_io.splent_feature_marketplace.services import DEFAULT_INDEX_URL


def inject_config(app):
    # setdefault: respect anything the product/.env already set; only fill gaps.
    app.config.setdefault(
        "SPLENT_INDEX_URL", os.getenv("SPLENT_INDEX_URL", DEFAULT_INDEX_URL)
    )
