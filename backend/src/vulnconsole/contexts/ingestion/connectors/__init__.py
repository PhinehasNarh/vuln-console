"""Built-in scanner connectors (ADR-0008). Importing this package registers them.

Order matters for sniffing: the most format-specific signatures go first.
"""

from vulnconsole.contexts.ingestion.connectors.base import register
from vulnconsole.contexts.ingestion.connectors.gitleaks import GitleaksConnector
from vulnconsole.contexts.ingestion.connectors.grype import GrypeConnector
from vulnconsole.contexts.ingestion.connectors.sarif import SarifConnector
from vulnconsole.contexts.ingestion.connectors.trivy import TrivyConnector
from vulnconsole.contexts.ingestion.connectors.trufflehog import TruffleHogConnector

register(TrivyConnector())
register(GrypeConnector())
register(GitleaksConnector())
register(TruffleHogConnector())
register(SarifConnector())
