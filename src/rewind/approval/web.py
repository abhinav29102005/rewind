import logging

logger = logging.getLogger(__name__)

class WebApprovalUI:
    """Local web UI for human approvals."""
    def __init__(self, port: int = 8080) -> None:
        self.port = port

    def start(self) -> None:
        logger.info(f"Starting Web Approval UI on port {self.port}")
        # Not fully implemented - placeholder for HTTP server

    def stop(self) -> None:
        logger.info("Stopping Web Approval UI")
