"""MyDNA: a local, private tool for looking up your variants in ClinVar."""

from __future__ import annotations

import logging

from flask import Flask

from mydna.config import Config

__version__ = "1.0.0"

__all__ = ["__version__", "create_app"]


def create_app(config: Config | None = None) -> Flask:
    """Build the application.

    This is the only Flask instance in the project. Extensions and error
    handlers attach here, so they actually take effect.
    """
    from mydna.core.repository import VariantRepository, create_index_engine
    from mydna.data.build_index import read_index_metadata
    from mydna.web.errors import register_error_handlers
    from mydna.web.routes import bp
    from mydna.web.security import register_security
    from mydna.web.store import ReportStore

    config = config or Config()
    app = Flask(__name__)
    app.config.update(config.as_flask_mapping())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    engine = create_index_engine(config.database_url)
    repository = VariantRepository(engine)

    app.extensions["mydna"] = {
        "config": config,
        "engine": engine,
        "repository": repository,
        "store": ReportStore(),
        "index_metadata": read_index_metadata(engine),
    }

    register_security(app)
    register_error_handlers(app)
    app.register_blueprint(bp)

    @app.context_processor
    def _inject_index_metadata() -> dict[str, object]:
        # The footer cites the ClinVar release on every page, including errors.
        return {"index_metadata": app.extensions["mydna"]["index_metadata"]}

    if config.secret_key_is_ephemeral:
        app.logger.info(
            "No MYDNA_SECRET_KEY set; generated an ephemeral one. "
            "Sessions will not survive a restart."
        )

    return app
