"""
Temporal client for starting workflows.
"""

from temporalio.client import Client
from typing import Optional
import os

from app.temporal_workflows.query_workflow import QueryRequest, QueryResponse


TASK_QUEUE = "vector-db-query-queue"


class TemporalQueryClient:
    """
    Client for executing queries via Temporal workflows.
    """
    
    def __init__(self, temporal_url: str | None = None):
        # Allow env override when running in Docker: TEMPORAL_ADDRESS=temporal:7233
        self.temporal_url = temporal_url or os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        self._client: Optional[Client] = None
    
    async def connect(self):
        """Connect to Temporal server."""
        if not self._client:
            self._client = await Client.connect(self.temporal_url)
    
    async def execute_query(self, request: QueryRequest) -> dict:
        """
        Execute a query via Temporal workflow.
        Returns the query results as a dict (Temporal serializes dataclasses).
        """
        await self.connect()
        
        # Start workflow
        handle = await self._client.start_workflow(
            "QueryWorkflow",
            request,
            id=f"query-{request.lib_id}-{id(request)}",
            task_queue=TASK_QUEUE,
        )
        
        # Wait for result (Temporal returns dataclass as dict)
        result = await handle.result()
        
        # Convert QueryResponse dataclass to dict if needed
        if hasattr(result, '__dict__'):
            from dataclasses import asdict
            return asdict(result)
        return result
    
    async def get_workflow_status(self, workflow_id: str) -> dict:
        """
        Query workflow status.
        """
        await self.connect()
        
        handle = self._client.get_workflow_handle(workflow_id)
        status = await handle.query("get_status")
        return status
    
    async def cancel_workflow(self, workflow_id: str):
        """
        Signal workflow to cancel.
        """
        await self.connect()
        
        handle = self._client.get_workflow_handle(workflow_id)
        await handle.signal("cancel_query")

