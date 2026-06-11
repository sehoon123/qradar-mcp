"""AQL query templates resource."""

import json
from typing import Any, Dict

from .base import MCPResource


class AQLQueryTemplatesResource(MCPResource):
    """Resource providing safe AQL query templates for common investigations."""

    @property
    def uri(self) -> str:
        return "qradar://aql/templates"

    @property
    def name(self) -> str:
        return "AQL Query Templates"

    @property
    def description(self) -> str:
        return "Structured AQL templates for common QRadar investigation workflows."

    @property
    def mime_type(self) -> str:
        return "application/json"

    async def read(self) -> Dict[str, Any]:
        templates = {
            "workflow": [
                "Read qradar://aql/fields/events or qradar://aql/fields/flows first.",
                "Select the closest template and substitute placeholders.",
                "Validate the final query with validate_aql before create_ariel_search.",
            ],
            "templates": [
                {
                    "name": "offense_events",
                    "database": "events",
                    "placeholders": ["offense_id", "limit", "minutes"],
                    "query": (
                        "SELECT starttime, sourceip, destinationip, username, qid, "
                        "QIDDESCRIPTION(qid) AS event_name, LOGSOURCENAME(logsourceid) AS log_source, magnitude "
                        "FROM events WHERE INOFFENSE({offense_id}) "
                        "ORDER BY starttime DESC LIMIT {limit} LAST {minutes} MINUTES"
                    ),
                },
                {
                    "name": "top_source_ips",
                    "database": "events",
                    "placeholders": ["limit", "hours"],
                    "query": (
                        "SELECT sourceip, COUNT(*) AS event_count FROM events "
                        "GROUP BY sourceip ORDER BY event_count DESC LIMIT {limit} LAST {hours} HOURS"
                    ),
                },
                {
                    "name": "failed_logins_by_user_source",
                    "database": "events",
                    "placeholders": ["threshold", "limit", "hours"],
                    "query": (
                        "SELECT username, sourceip, COUNT(*) AS attempts FROM events "
                        "WHERE category IN (3003, 3005, 3010) "
                        "GROUP BY username, sourceip HAVING COUNT(*) > {threshold} "
                        "ORDER BY attempts DESC LIMIT {limit} LAST {hours} HOURS"
                    ),
                },
                {
                    "name": "flow_protocol_summary",
                    "database": "flows",
                    "placeholders": ["limit", "hours"],
                    "query": (
                        "SELECT PROTOCOLNAME(protocolid) AS protocol, SUM(sourcebytes + destinationbytes) AS bytes "
                        "FROM flows GROUP BY protocol ORDER BY bytes DESC LIMIT {limit} LAST {hours} HOURS"
                    ),
                },
            ],
        }
        return {
            "contents": [
                {
                    "uri": self.uri,
                    "mimeType": self.mime_type,
                    "text": json.dumps(templates, indent=2),
                }
            ]
        }
