"""List QVM vulnerability instance result instances."""

from qradar_mcp.tools.qvm.list_qvm_vuln_instance_result_assets import ListQvmVulnInstanceResultAssetsTool


class ListQvmVulnInstanceResultInstancesTool(ListQvmVulnInstanceResultAssetsTool):
    tool_name = "list_qvm_vuln_instance_result_instances"
    tool_description = "List vulnerability instances returned by a QVM vulnerability instance search task."

    async def _execute_impl(self, arguments):
        task_id = arguments.get("task_id")
        if not task_id:
            return self.create_error_response("Error: task_id is required")
        self.endpoint = f"/qvm/saved_searches/vuln_instances/{task_id}/results/vuln_instances"
        return await super(ListQvmVulnInstanceResultAssetsTool, self)._execute_impl(arguments)
