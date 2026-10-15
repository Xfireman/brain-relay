from threading import Event
from brain_relay.jobs import Jobs, QueueFull
import pytest


def test_queue_rejects_extra_work_without_leaking_slots():
    jobs=Jobs(capacity=1)
    release=Event()
    first=jobs.submit(lambda:release.wait(2))
    try:
        with pytest.raises(QueueFull):jobs.submit(lambda:None)
        assert jobs.get(first)['status'] in ('queued','running')
    finally:
        release.set();jobs.pool.shutdown(wait=True)
    assert jobs.get(first)['status']=='succeeded'


def test_retention_evicts_completed_results_and_unknown_id_is_missing():
    jobs=Jobs(capacity=2,retained=2,ttl=0)
    first=jobs.submit(lambda:{'draft':'sample'})
    jobs.pool.shutdown(wait=True)
    assert jobs.get(first) is None
    assert jobs.get('unknown') is None


def test_errors_never_expose_exception_body():
    jobs=Jobs()
    def bad():raise RuntimeError('Authorization: synthetic-secret')
    task=jobs.submit(bad)
    jobs.pool.shutdown(wait=True)
    assert jobs.get(task)=={'status':'failed','error':'provider_failed'}
