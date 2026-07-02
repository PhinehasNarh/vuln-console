"""Built-in scanner connectors (ADR-0008). Importing this package registers them."""

from vulnconsole.contexts.ingestion.connectors.base import register
from vulnconsole.contexts.ingestion.connectors.sarif import SarifConnector

register(SarifConnector())
