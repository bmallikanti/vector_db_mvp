"""
Temporal worker for executing workflows and activities.
"""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal_workflows.query_workflow import (
    QueryWorkflow,
    validate_query_activity,
    setup_test_data_activity,
    generate_embedding_activity,
    search_vectors_activity,
    rerank_results_activity,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TASK_QUEUE = "vector-db-query-queue"


async def main():
    """
    Start the Temporal worker.
    """
    logger.info("Connecting to Temporal server at localhost:7233...")
    # Connect to Temporal server (default: localhost:7233)
    client = await Client.connect("localhost:7233")
    logger.info("✓ Connected to Temporal server")
    
    # Create worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[QueryWorkflow],
        activities=[
            setup_test_data_activity,
            validate_query_activity,
            generate_embedding_activity,
            search_vectors_activity,
            rerank_results_activity,
        ],
    )
    
    logger.info(f"Starting worker on task queue: {TASK_QUEUE}")
    logger.info("Worker is ready to process workflows and activities...")
    logger.info("Waiting for tasks...")
    
    # Run worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

