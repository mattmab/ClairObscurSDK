"""Recoverable Picto ownership transactions using the existing guarded native API.

Reflection reads are submitted to the caller's reader worker. ``poll`` belongs
on the mod owner thread: native sessions deliberately reject cross-thread use.
The existing transport call is synchronous (and has its own bounded timeout);
this class does not weaken that contract or retry an ambiguous mutation.
"""
from time import monotonic
from math import isfinite

from .picto_progression import change


class UnlockTransaction:
    STATES = ('Ready', 'Unlocking', 'Unlocked', 'Already Owned', 'Removing', 'Removed', 'Already Absent', 'Failed', 'Timed Out')

    def __init__(self, ownership, submit_read, *, desired=True, timeout=20., clock=monotonic):
        if not isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError('Unlock timeout must be in (0, 120] seconds')
        if type(desired) is not bool:
            raise ValueError('Desired Picto ownership must be boolean')
        self._desired = desired
        self.ownership, self.submit_read = ownership, submit_read
        self.timeout, self.clock = timeout, clock
        self.state, self.identity, self.error = 'Ready', None, None
        self.future, self.phase = None, None
        self.timings, self.dispatched = {}, False
        self.owned = dict(ownership.owned)

    @property
    def desired(self):
        return self._desired

    @property
    def success_state(self):
        return 'Unlocked' if self.desired else 'Removed'

    @property
    def unchanged_state(self):
        return 'Already Owned' if self.desired else 'Already Absent'

    @property
    def busy(self):
        return self.state in ('Unlocking', 'Removing')

    def _finish(self, state, error=None):
        self.state, self.error = state, error
        self.timings['total'] = self.clock() - self.started
        return state

    def _submit(self, phase, callback):
        self.phase, self.phase_started = phase, self.clock()
        self.future = self.submit_read(callback)

    def start(self, identity):
        # A timed-out reader may still own the pinned reader. Never stack work
        # behind it or dispatch a second operation while it is unresolved.
        if self.busy or (self.future is not None and not self.future.done()):
            return False
        self.identity, self.state, self.error = identity, ('Unlocking' if self.desired else 'Removing'), None
        self.started = self.clock()
        self.dispatched, self.timings, self.dispatch_error = False, {}, None
        self.future = None
        row = self.ownership.rows.get(identity)
        if not isinstance(identity, str) or row is None or not row.get('normal') or row.get('asset') is None:
            self._finish('Failed', 'Experimental or unverified Picto is excluded from gameplay ownership operations')
            return True
        self.asset_identity = self._identity(row['asset'])
        try:
            self._submit('preflight', self._refresh)
        except Exception as error:
            self._finish('Failed', str(error))
        return True

    @staticmethod
    def _identity(obj):
        return obj.index, obj.serial, obj.address

    def _refresh(self):
        # Actual authoritative ItemInstances read, not the catalog's UI cache.
        return dict(self.ownership.refresh())

    def _dispatch(self):
        row = self.ownership.rows.get(self.identity)
        if row is None or not row.get('normal') or row.get('asset') is None or self._identity(row['asset']) != self.asset_identity:
            raise RuntimeError('Selected Picto identity changed before ownership mutation')
        owner = self.ownership
        owner.scope._check()
        # Native checks every dependency identity, static row mapping, both
        # ownership stores, script shapes and dispatch target before mutation.
        return change(owner.scope, 10, owner.manager,
                      owner.function('AC_jRPG_InventoryManager_C', 'AddItemToInventory' if self.desired else 'RemoveItemFromInventory'),
                      row['asset'], owner.table, owner.gi, int(not self.desired), int(self.desired))

    def poll(self):
        if not self.busy:
            return self.state
        if self.future is None:
            return self._finish('Failed', 'Ownership reader was not scheduled')
        if not self.future.done():
            if self.clock() - self.started >= self.timeout:
                self.future.cancel()  # Only read work; cancellation is best effort.
                return self._finish('Timed Out', 'Ownership read timed out; check inventory before retrying')
            return self.state
        try:
            self.owned = dict(self.future.result())
        except Exception as error:
            self.future = None
            return self._finish('Timed Out' if isinstance(error, TimeoutError) else 'Failed', str(error))
        self.future = None
        self.timings[self.phase] = self.clock() - self.phase_started
        if self.phase == 'verify':
            if (self.identity in self.owned) == self.desired:
                return self._finish(self.success_state)
            if self.clock() - self.started >= self.timeout or isinstance(self.dispatch_error, TimeoutError):
                return self._finish('Timed Out', str(self.dispatch_error or 'Ownership completion timed out'))
            return self._finish('Failed', str(self.dispatch_error or 'Inventory did not confirm requested ownership'))
        if (self.identity in self.owned) == self.desired:
            return self._finish(self.unchanged_state)
        if self.clock() - self.started >= self.timeout:
            return self._finish('Timed Out', 'Preflight expired before dispatch')
        started = self.clock()
        try:
            self.dispatched = True
            observed = self._dispatch()
            if observed != int(self.desired):
                raise RuntimeError('Native acknowledgement did not confirm requested ownership')
        except Exception as error:
            if not self.desired and 'error=1759,' in str(error):
                error = RuntimeError('Equipped Picto protected: unequip it from every expeditioner before removing it')
            self.dispatch_error = error
        finally:
            self.timings['dispatch_transport'] = self.clock() - started
        # Always reconcile after an ambiguous native acknowledgement. Readback
        # may prove success even if the transport lost the acknowledgement.
        try:
            self._submit('verify', self._refresh)
        except Exception as error:
            return self._finish('Failed', 'Ownership verification unavailable: ' + str(error))
        return self.state


class BulkUnlockTransaction:
    """Confirmed gameplay ownership changes, one guarded transaction at a time.

    The UI must present ``total`` and obtain confirmation before calling start.
    Re-running after partial failure reads ownership anew and skips successes.
    """
    def __init__(self, transaction, *, timeout=300., clock=monotonic):
        if not isfinite(timeout) or not 0 < timeout <= 3600:
            raise ValueError('Bulk timeout must be in (0, 3600] seconds')
        self.transaction, self.clock, self.timeout = transaction, clock, timeout
        owner = transaction.ownership
        self.queue = sorted(identity for identity, row in owner.rows.items()
                            if row.get('normal') and (identity in owner.owned) != transaction.desired)
        self.total = len(self.queue)
        self.completed, self.skipped, self.failed = [], [], {}
        self.done, self.started, self.active = False, None, None
        self.error = None

    def start(self):
        if self.started is None:
            self.started = self.clock()

    def stop(self):
        self.queue.clear()
        if self.active is None:
            self.done = True

    def poll(self):
        if self.done or self.started is None:
            return
        if self.clock() - self.started >= self.timeout:
            self.queue.clear()
            self.error = 'Bulk ownership time limit reached'
        tx = self.transaction
        if self.active is not None:
            state = tx.poll()
            if tx.busy:
                return
            identity, self.active = self.active, None
            if state == tx.success_state:
                self.completed.append(identity)
            elif state == tx.unchanged_state:
                self.skipped.append(identity)
            else:
                self.failed[identity] = tx.error or state
            # A timed-out worker cannot safely be reused while still running.
            if tx.future is not None and not tx.future.done():
                self.queue.clear()
                self.error = 'Reader is still pending; remaining operations were not dispatched'
            return
        if not self.queue:
            self.done = True
            return
        identity = self.queue[0]
        if tx.start(identity):
            self.active = self.queue.pop(0)
