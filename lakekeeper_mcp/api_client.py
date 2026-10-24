"""Public client facade for lakekeeper_mcp."""

from lakekeeper_mcp.api.api_client_lakekeeper import LakekeeperApi, LakekeeperApiError

__all__ = ["Api", "LakekeeperApiError"]


class Api(LakekeeperApi):
    """Authenticated Lakekeeper (Iceberg REST catalog) client."""

    pass
