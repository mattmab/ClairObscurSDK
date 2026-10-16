"""Owner-thread startup driver for the same guarded interactive frame queue."""
import time
from concurrent.futures import Future
from .picto_batch import FrameBulkTransaction
from .picto_transactions import UnlockTransaction


class ProgressionOwner:
    """Owned-item queue context; no inventory grant/removal capabilities."""
    def __init__(self,scope,catalog,owned,gi,table):
        self.scope,self.catalog,self.owned,self.gi,self.table=scope,catalog,owned,gi,table
    def refresh(self):
        from .picto_inventory import owned_pictos
        self.catalog,self.owned=owned_pictos(self.scope.pid,catalog=self.catalog)
        return self.owned


def run(owner, identities, *, level=None, mastery=None, desired=True, timeout=65.):
    # Startup already owns a scoped read worker. No other thread accesses the
    # session, and native game work remains frame paced on the game thread.
    def read(callback):
        future=Future()
        try:future.set_result(callback())
        except Exception as error:future.set_exception(error)
        return future
    job=FrameBulkTransaction(UnlockTransaction(owner,read,desired=desired),level=level,
                             mastery=mastery,identities=identities)
    deadline=time.monotonic()+timeout
    job.start()
    while not job.done:
        if time.monotonic()>deadline:
            job.stop()
            raise RuntimeError('Picto startup batch timed out; no resubmission')
        job.poll()
        if not job.done and job.phase=='running':time.sleep(.02)
    if job.error or job.failed or len(job.completed)+len(job.skipped)!=job.total:
        raise RuntimeError(f'Picto startup batch incomplete: {job.error or job.failed}')
    return job.completed
