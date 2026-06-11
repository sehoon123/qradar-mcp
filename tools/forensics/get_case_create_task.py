"""Get QRadar forensics case create task."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetCaseCreateTaskTool(SimpleGetByIdTool):
    tool_name = "get_case_create_task"
    tool_description = "Get a QRadar Incident Forensics case create task by ID."
    endpoint_template = "/forensics/case_management/case_create_tasks/{task_id}"
    id_argument = "task_id"
    id_description = "Case create task ID"
