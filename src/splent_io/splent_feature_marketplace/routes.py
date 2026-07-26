from flask import abort, redirect, render_template, request, url_for

from splent_io.splent_feature_marketplace import marketplace_bp
from splent_framework.services.service_locator import service_proxy

marketplace_service = service_proxy("MarketplaceService")


@marketplace_bp.route("/marketplace", methods=["GET"])
def index():
    """Public catalog: feature grid with free-text search and filters."""
    query = (request.args.get("q") or "").strip()
    archetype = (request.args.get("archetype") or "").strip() or None
    category = (request.args.get("category") or "").strip() or None

    features = marketplace_service.search(
        query=query or None, category=category, archetype=archetype
    )
    return render_template(
        "marketplace/index.html",
        features=features,
        query=query,
        archetype=archetype,
        category=category,
        archetypes=marketplace_service.archetypes(),
        categories=marketplace_service.categories(),
        total_features=len(marketplace_service.all_features()),
        total_spls=len(marketplace_service.spls()),
    )


@marketplace_bp.route("/marketplace/spls", methods=["GET"])
def spls():
    """The SPLs of the index, with their mandatory/optional/alternative features."""
    # An SPL model may reference features that are not published in the index
    # (e.g. only on GitHub/PyPI): those render as unlinked "external" chips
    # instead of pointing to a detail page that would 404.
    known_shorts = {
        feature.get("short") for feature in marketplace_service.all_features()
    }
    # SOFT dependency on the configurator feature: the "Configure this line"
    # CTA only renders when the product actually installs it. The URL is
    # built here (not in the template) so the reference stays behind the
    # runtime guard.
    from flask import current_app

    has_configurator = "configurator.configure" in current_app.view_functions
    spl_views = []
    for spl in marketplace_service.spls():
        model_features = (spl.get("model") or {}).get("features") or {}
        mandatory, optional, groups = [], [], {}
        for short, meta in model_features.items():
            entry = dict(
                meta if isinstance(meta, dict) else {},
                short=short,
                external=short not in known_shorts,
            )
            group = entry.get("group")
            if group:
                bucket = groups.setdefault(
                    group, {"kind": entry.get("group_kind"), "options": []}
                )
                bucket["options"].append(entry)
            elif entry.get("presence") == "mandatory":
                mandatory.append(entry)
            else:
                optional.append(entry)
        spl_views.append(
            {
                "name": spl.get("name"),
                "description": spl.get("description"),
                "uvl": spl.get("uvl") or {},
                "mandatory": sorted(mandatory, key=lambda e: e["short"]),
                "optional": sorted(optional, key=lambda e: e["short"]),
                "groups": groups,
                "configure_url": (
                    url_for("configurator.configure", spl_name=spl.get("name"))
                    if has_configurator
                    else None
                ),
            }
        )
    return render_template("marketplace/spls.html", spls=spl_views)


@marketplace_bp.route("/marketplace/publish", methods=["GET"])
def publish():
    """How third parties publish: release on GitHub + PR to the registry.

    Static rules outrank converter rules in werkzeug, so this never falls
    through to detail(<short>) even though both share the prefix.
    """
    return render_template("marketplace/publish.html")


@marketplace_bp.route("/marketplace/<short>", methods=["GET"])
def detail(short):
    """Full feature sheet: contract, dependencies, install command."""
    feature = marketplace_service.find(short)
    if feature is None:
        abort(404)

    github = feature.get("github")
    if isinstance(github, str) and github:
        repo_url = github
    elif isinstance(github, dict) and github.get("url"):
        repo_url = github["url"]
    else:
        repo_url = f"https://github.com/{feature.get('org')}/{feature.get('repo')}"

    pypi = feature.get("pypi")
    pypi_version = None
    if isinstance(pypi, dict):
        pypi_version = pypi.get("version")
    elif isinstance(pypi, str):
        pypi_version = pypi

    return render_template(
        "marketplace/detail.html",
        feature=feature,
        repo_url=repo_url,
        pypi_version=pypi_version,
        on_pypi=bool(pypi),
        install_command=f"splent feature:install {feature.get('id')}",
        collisions=marketplace_service.collisions_for(feature.get("short")),
    )


@marketplace_bp.route("/")
def home():
    """The catalog is this product's landing page."""
    return redirect(url_for("marketplace.index"))
