"""Celery task entrypoints wrapping async service logic."""

import asyncio
import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.worker.tasks.execute_outreach_step", bind=True, max_retries=3)
def execute_outreach_step(self, message_id: int):
    from app.services.sequence_engine import sequence_engine

    try:
        _run_async(sequence_engine.execute_step(message_id))
    except Exception as exc:
        logger.exception("execute_outreach_step failed for message %s", message_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="app.worker.tasks.poll_inbox_for_replies")
def poll_inbox_for_replies():
    from app.services.reply_detector import reply_detector

    _run_async(reply_detector.poll_inbox())


@celery_app.task(name="app.worker.tasks.sweep_overdue_messages")
def sweep_overdue_messages():
    from app.services.sequence_engine import sequence_engine

    _run_async(sequence_engine.sweep_overdue_messages())
