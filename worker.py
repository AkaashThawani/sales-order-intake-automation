#!/usr/bin/env python3
"""
Background worker for automated sales order processing.
Handles email fetching, workflow processing, and task execution.
"""

import time
import schedule
import signal
import sys
from datetime import datetime, timedelta
from core.workflow_processor import WorkflowProcessor
from core.email_manager import EmailManager
from models import SessionLocal, WorkflowTask, Order
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SalesOrderWorker:
    """Background worker for automated sales order processing"""

    def __init__(self):
        self.workflow_processor = WorkflowProcessor()
        self.email_manager = EmailManager()
        self.running = True
        self.last_email_check = None
        self.last_workflow_check = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Sales Order Worker initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def start(self):
        """Start the worker with scheduled tasks"""
        logger.info("Starting Sales Order Worker...")

        # Schedule tasks
        schedule.every(2).minutes.do(self._process_emails)
        schedule.every(1).minutes.do(self._process_workflows)
        schedule.every(5).minutes.do(self._cleanup_old_tasks)
        schedule.every(1).hours.do(self._health_check)

        # Run initial tasks
        logger.info("Running initial tasks...")
        self._process_emails()
        self._process_workflows()

        # Main loop
        logger.info("Worker started. Press Ctrl+C to stop.")
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(30)  # Wait before retrying

        logger.info("Worker stopped gracefully")

    def _process_emails(self):
        """Fetch and process new emails"""
        try:
            if self.last_email_check and (datetime.now() - self.last_email_check) < timedelta(minutes=1):
                return  # Don't check too frequently

            logger.info("Checking for new emails...")
            processed_emails = self.email_manager.fetch_and_process_emails()

            if processed_emails:
                logger.info(f"Processed {len(processed_emails)} emails")
                for email_info in processed_emails:
                    email_data = email_info['email_data']
                    result = self.workflow_processor.process_email(email_data)
                    logger.info(f"Email {email_data['id']} processed: {result['actions_taken']}")
            else:
                logger.debug("No new emails to process")

            self.last_email_check = datetime.now()

        except Exception as e:
            logger.error(f"Error processing emails: {e}")

    def _process_workflows(self):
        """Process pending workflow tasks"""
        try:
            if self.last_workflow_check and (datetime.now() - self.last_workflow_check) < timedelta(seconds=30):
                return  # Don't check too frequently

            logger.info("Processing workflow tasks...")
            self.workflow_processor.process_pending_orders()
            logger.debug("Workflow processing completed")

            self.last_workflow_check = datetime.now()

        except Exception as e:
            logger.error(f"Error processing workflows: {e}")

    def _cleanup_old_tasks(self):
        """Clean up old completed/failed tasks"""
        try:
            db = SessionLocal()
            # Delete tasks older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)

            deleted_count = db.query(WorkflowTask).filter(
                WorkflowTask.status.in_(['completed', 'failed']),
                WorkflowTask.completed_at < cutoff_date
            ).delete()

            db.commit()
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old workflow tasks")

        except Exception as e:
            logger.error(f"Error cleaning up tasks: {e}")
        finally:
            db.close()

    def _health_check(self):
        """Perform health checks and log system status"""
        try:
            db = SessionLocal()

            # Get system stats
            total_orders = db.query(Order).count()
            pending_tasks = db.query(WorkflowTask).filter(WorkflowTask.status == 'pending').count()
            failed_tasks = db.query(WorkflowTask).filter(WorkflowTask.status == 'failed').count()

            logger.info(f"Health Check - Orders: {total_orders}, Pending Tasks: {pending_tasks}, Failed Tasks: {failed_tasks}")

            # Alert if too many failed tasks
            if failed_tasks > 10:
                logger.warning(f"High number of failed tasks: {failed_tasks}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")
        finally:
            db.close()

    def run_once(self):
        """Run all tasks once (for testing/manual execution)"""
        logger.info("Running all tasks once...")

        try:
            self._process_emails()
            self._process_workflows()
            self._cleanup_old_tasks()
            self._health_check()
            logger.info("All tasks completed successfully")
        except Exception as e:
            logger.error(f"Error running tasks: {e}")
            raise

def main():
    """Main entry point"""
    worker = SalesOrderWorker()

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once for testing
        worker.run_once()
    else:
        # Run continuously
        worker.start()

if __name__ == "__main__":
    main()
