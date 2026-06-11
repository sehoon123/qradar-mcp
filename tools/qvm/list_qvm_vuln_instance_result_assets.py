"""List QVM vulnerability instance result assets."""

from qradar_mcp.tools.schema import schema
from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmVulnInstanceResultAssetsTool(SimpleListTool):
    tool_name = "list_qvm_vuln_instance_result_assets"
    tool_description = "List assets returned by a QVM vulnerability instance search task."
    endpoint = ""

    async def _execute_impl(self, arguments):
        task_id = arguments.get("task_id")
        if not task_id:
            return self.create_error_response("Error: task_id is required")
        self.endpoint = f"/qvm/saved_searches/vuln_instances/{task_id}/results/assets"
        return await super()._execute_impl(arguments)

    @property
    def input_schema(self):
        return (schema()
            .string("task_id")
                .description("QVM vulnerability instance task ID")
                .min_length(1)
                .required()
            .string("filter")
                .description("Optional QRadar filter expression")
            .string("sort")
                .description("Optional sort expression, e.g. '+name' or '-id'")
            .integer("limit")
                .description(f"Maximum rows to return (default: {self.default_limit})")
                .minimum(1)
                .maximum(self.max_limit)
                .default(self.default_limit)
            .integer("offset")
                .description("Number of rows to skip (default: 0)")
                .minimum(0)
                .default(0)
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())
