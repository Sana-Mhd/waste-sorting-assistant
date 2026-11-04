"""The JSON API of the app: the data of the dashboard for other programs.

    GET /api/regions                 the known regions
    GET /api/rules?region=DO         the bin for every category
    GET /api/results?region=DO       every stored scan, oldest first
    GET /api/summary?region=DO       the headline numbers of the dashboard

Without ?region= the default region is used. An unknown region gets a 404.
All data comes through the services of subsystems 2 and 3, never from SQLite directly.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from data_rules import ClassificationRecord, DataRulesError, UnknownRegionError

from .config import WebConfig
from .services import AppServices

logger = logging.getLogger(__name__)


def record_to_json(record: ClassificationRecord) -> dict:
    """One stored scan as plain JSON values. The database stores times in UTC."""
    return {**asdict(record), "created_at": f"{record.created_at.isoformat()}Z"}


def create_api(services: AppServices, config: WebConfig) -> Blueprint:
    """Build the /api routes.

    Args:
        services: the services of subsystems 1-3.
        config: settings of the web interface, for the default region.
    """
    api = Blueprint("api", __name__, url_prefix="/api")

    def requested_region() -> str:
        """The region in the address, or the default one.

        Raises:
            UnknownRegionError: if the database does not know the region.
        """
        code = (request.args.get("region") or config.default_region).strip().upper()
        if not services.dal.region_exists(code):
            raise UnknownRegionError(f"unknown region {code!r}")
        return code

    @api.get("/regions")
    def regions() -> ResponseReturnValue:
        return jsonify([{"code": code, "name": name} for code, name in services.regions()])

    @api.get("/rules")
    def rules() -> ResponseReturnValue:
        return jsonify([asdict(rule) for rule in services.dal.get_rules(requested_region())])

    @api.get("/results")
    def results() -> ResponseReturnValue:
        records = services.dal.get_results(region_code=requested_region())
        return jsonify([record_to_json(record) for record in records])

    @api.get("/summary")
    def summary() -> ResponseReturnValue:
        return jsonify(asdict(services.analytics.summary(requested_region())))

    @api.errorhandler(UnknownRegionError)
    def unknown_region(error: UnknownRegionError) -> ResponseReturnValue:
        return jsonify(error=str(error)), 404

    @api.errorhandler(DataRulesError)
    def data_problem(error: DataRulesError) -> ResponseReturnValue:
        logger.error("API request failed: %s", error)
        return jsonify(error="The data could not be read."), 503

    return api
