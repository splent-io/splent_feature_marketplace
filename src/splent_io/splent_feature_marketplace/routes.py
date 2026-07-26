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
    )


@marketplace_bp.route("/marketplace/spls", methods=["GET"])
def spls():
    """The SPLs of the index, with their mandatory/optional/alternative features."""
    spl_views = []
    for spl in marketplace_service.spls():
        model_features = (spl.get("model") or {}).get("features") or {}
        mandatory, optional, groups = [], [], {}
        for short, meta in model_features.items():
            entry = dict(meta or {}, short=short)
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
            }
        )
    return render_template("marketplace/spls.html", spls=spl_views)


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
