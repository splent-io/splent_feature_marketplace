from flask import url_for
from flask_babel import gettext as _

from splent_framework.hooks.template_hooks import register_template_hook


def marketplace_sidebar_links():
    return (
        '<li class="sidebar-item">'
        f'<a class="sidebar-link" href="{url_for("marketplace.index")}">'
        '<i class="align-middle" data-feather="package"></i> '
        f'<span class="align-middle">{_("Marketplace")}</span>'
        "</a>"
        "</li>"
        '<li class="sidebar-item">'
        f'<a class="sidebar-link" href="{url_for("marketplace.spls")}">'
        '<i class="align-middle" data-feather="layers"></i> '
        f'<span class="align-middle">{_("Product lines")}</span>'
        "</a>"
        "</li>"
    )


register_template_hook("layout.sidebar.top", marketplace_sidebar_links)
