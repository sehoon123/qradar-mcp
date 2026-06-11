"""List QVM vulnerability instance result vulnerabilities."""

from qradar_mcp.tools.qvm.list_qvm_vuln_instance_result_assets import ListQvmVulnInstanceResultAssetsTool


class ListQvmVulnInstanceResultVulnerabilitiesTool(ListQvmVulnInstanceResultAssetsTool):
    tool_name = "list_qvm_vuln_instance_result_vulnerabilities"
    tool_description = "List vulnerabilities returned by a QVM vulnerability instance search task."

    async def _execute_impl(self, arguments):
        task_id = arguments.get("task_id")
        if not task_id:
            return self.create_error_response("Error: task_id is required")
        self.endpoint = f"/qvm/saved_searches/vuln_instances/{task_id}/results/vulnerabilities"
        return await super(ListQvmVulnInstanceResultAssetsTool, self)._execute_impl(arguments)
