import unittest
from concurrent.futures import Future
from types import SimpleNamespace as NS
from unittest.mock import patch

from expedition33.picto_transactions import UnlockTransaction, BulkUnlockTransaction


class UnlockTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.
        self.tasks = []
        self.actual = {}
        self.owner = NS(rows={k: {'normal': k != 'Test', 'asset': NS(index=i, serial=1, address=100+i)}
                              for i, k in enumerate(('A', 'B', 'Test'))}, owned={},
                        scope=NS(_check=lambda: None), manager=object(), table=object(), gi=object(),
                        function=lambda *args: object())
        def refresh():
            self.owner.owned = dict(self.actual)
            return self.owner.owned
        self.owner.refresh = refresh
        self.tx = UnlockTransaction(self.owner, self.submit, timeout=5, clock=lambda: self.now)

    def submit(self, callback):
        future = Future()
        self.tasks.append((future, callback))
        return future

    def finish_read(self):
        future, callback = self.tasks.pop(0)
        if future.cancelled():
            return
        try:
            future.set_result(callback())
        except Exception as error:
            future.set_exception(error)

    def unlock(self, *args):
        self.actual[self.tx.identity] = ('item', 1)
        return 1

    def complete(self):
        self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=self.unlock):
            self.tx.poll()
        self.finish_read()
        self.tx.poll()

    def test_success_requires_readback_and_duplicate_is_skipped(self):
        self.assertTrue(self.tx.start('A'))
        self.assertFalse(self.tx.start('A'))
        self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=self.unlock) as dispatch:
            self.tx.poll()
            self.assertEqual(self.tx.state, 'Unlocking')
            self.finish_read()
            self.assertEqual(self.tx.poll(), 'Unlocked')
            self.tx.start('A'); self.finish_read()
            self.assertEqual(self.tx.poll(), 'Already Owned')
            self.assertEqual(dispatch.call_count, 1)
        self.assertFalse(self.tx.busy)

    def test_experimental_and_missing_identity_excluded(self):
        for identity in ('Test', 'Missing'):
            self.assertTrue(self.tx.start(identity))
            self.assertEqual(self.tx.state, 'Failed')
            self.assertFalse(self.tasks)

    def test_stale_selected_asset_is_not_dispatched(self):
        self.tx.start('A'); self.finish_read()
        self.owner.rows['A']['asset'].serial = 2
        with patch('expedition33.picto_transactions.change') as dispatch:
            self.tx.poll(); self.finish_read(); self.tx.poll()
            dispatch.assert_not_called()
        self.assertEqual(self.tx.state, 'Failed')
        self.assertIn('identity changed', self.tx.error)

    def test_native_failure_releases_busy_and_new_request_can_succeed(self):
        self.tx.start('A'); self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=RuntimeError('error=1753')):
            self.tx.poll()
        self.finish_read(); self.tx.poll()
        self.assertEqual(self.tx.state, 'Failed')
        self.assertFalse(self.tx.busy)
        self.tx.start('B'); self.complete()
        self.assertEqual(self.tx.state, 'Unlocked')

    def test_lost_ack_is_reconciled_without_second_mutation(self):
        def lost(*args):
            self.unlock()
            raise TimeoutError('lost acknowledgement')
        self.tx.start('A'); self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=lost) as dispatch:
            self.tx.poll(); self.finish_read(); self.tx.poll()
            self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(self.tx.state, 'Unlocked')

    def test_pending_timeout_releases_ui_but_blocks_stacked_worker(self):
        self.tx.start('A')
        self.tasks[0][0].set_running_or_notify_cancel()
        self.now = 6
        self.assertEqual(self.tx.poll(), 'Timed Out')
        self.assertFalse(self.tx.busy)
        self.assertFalse(self.tx.start('B'))
        self.finish_read()
        self.assertTrue(self.tx.start('B'))
        self.complete()
        self.assertEqual(self.tx.state, 'Unlocked')

    def test_readback_mismatch_never_reports_success(self):
        self.tx.start('A'); self.finish_read()
        with patch('expedition33.picto_transactions.change', return_value=1):
            self.tx.poll()
        self.finish_read(); self.tx.poll()
        self.assertEqual(self.tx.state, 'Failed')

    def test_bulk_partial_failure_continues_and_recovery_skips_owned(self):
        bulk = BulkUnlockTransaction(self.tx, clock=lambda: self.now)
        self.assertEqual(bulk.total, 2)
        bulk.start()
        def dispatch(*args):
            if self.tx.identity == 'A':
                raise RuntimeError('rejected')
            return self.unlock()
        with patch('expedition33.picto_transactions.change', side_effect=dispatch):
            for _ in range(15):
                bulk.poll()
                if self.tasks: self.finish_read()
        self.assertTrue(bulk.done)
        self.assertEqual(bulk.completed, ['B'])
        self.assertEqual(list(bulk.failed), ['A'])
        self.assertEqual(BulkUnlockTransaction(self.tx).queue, ['A'])

    def test_bulk_skips_owned_since_confirmation(self):
        bulk = BulkUnlockTransaction(self.tx, clock=lambda: self.now)
        self.actual['A'] = ('item', 1)
        bulk.start()
        with patch('expedition33.picto_transactions.change', side_effect=self.unlock):
            for _ in range(15):
                bulk.poll()
                if self.tasks: self.finish_read()
        self.assertEqual(bulk.skipped, ['A'])
        self.assertEqual(bulk.completed, ['B'])


class RemovalTests(unittest.TestCase):
    submit = UnlockTests.submit
    finish_read = UnlockTests.finish_read

    def setUp(self):
        UnlockTests.setUp(self)
        self.actual = {'A': ('first', 33), 'B': ('second', 12), 'Test': ('experimental', 1)}
        self.owner.owned = dict(self.actual)
        self.tx = UnlockTransaction(self.owner, self.submit, desired=False, timeout=5, clock=lambda: self.now)

    def remove(self, *args):
        self.actual.pop(self.tx.identity, None)
        return 0

    def test_removal_uses_native_remove_and_verifies_absence(self):
        from unittest.mock import Mock
        self.owner.function = Mock(return_value='remove_fn')
        self.tx.start('A')
        self.assertEqual(self.tx.state, 'Removing')
        self.assertTrue(self.tx.busy)
        self.assertFalse(self.tx.start('B'))
        self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=self.remove) as dispatch:
            self.tx.poll()
            self.assertEqual(dispatch.call_args.args[-2:], (1, 0))
            self.owner.function.assert_called_once_with('AC_jRPG_InventoryManager_C', 'RemoveItemFromInventory')
            self.assertEqual(self.tx.state, 'Removing')
            self.finish_read()
            self.assertEqual(self.tx.poll(), 'Removed')
            self.tx.start('A'); self.finish_read()
            self.assertEqual(self.tx.poll(), 'Already Absent')
            self.assertEqual(dispatch.call_count, 1)
        self.assertIn('B', self.tx.owned)
        self.assertNotIn('A', self.tx.owned)

    def test_rejected_equipped_item_is_preserved_and_bulk_continues(self):
        bulk = BulkUnlockTransaction(self.tx, clock=lambda: self.now)
        self.assertEqual(bulk.queue, ['A', 'B'])
        bulk.start()
        def dispatch(*args):
            if self.tx.identity == 'A':
                raise RuntimeError('Picto mutation rejected/partial: error=1759, outcome=0')
            return self.remove()
        with patch('expedition33.picto_transactions.change', side_effect=dispatch) as native:
            for _ in range(15):
                bulk.poll()
                if self.tasks: self.finish_read()
        self.assertTrue(bulk.done)
        self.assertEqual(bulk.completed, ['B'])
        self.assertEqual(list(bulk.failed), ['A'])
        self.assertIn('Equipped Picto protected', bulk.failed['A'])
        self.assertIn('A', self.actual)
        self.assertIn('Test', self.actual)
        self.assertEqual(native.call_count, 2)

    def test_removal_lost_ack_reconciles_absence_without_retry(self):
        def dispatch(*args):
            self.remove()
            raise TimeoutError('lost response')
        self.tx.start('A'); self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=dispatch) as native:
            self.tx.poll(); self.finish_read(); self.tx.poll()
            native.assert_called_once()
        self.assertEqual(self.tx.state, 'Removed')

    def test_removal_ack_without_absence_fails(self):
        self.tx.start('A'); self.finish_read()
        with patch('expedition33.picto_transactions.change', return_value=0): self.tx.poll()
        self.finish_read(); self.tx.poll()
        self.assertEqual(self.tx.state, 'Failed')
        self.assertIn('A', self.tx.owned)

    def test_cancel_bulk_finishes_active_verification_without_next_dispatch(self):
        bulk = BulkUnlockTransaction(self.tx, clock=lambda: self.now)
        bulk.start(); bulk.poll(); self.finish_read()
        with patch('expedition33.picto_transactions.change', side_effect=self.remove) as native:
            bulk.poll()
            bulk.stop()
            self.finish_read()
            bulk.poll(); bulk.poll()
            native.assert_called_once()
        self.assertTrue(bulk.done)
        self.assertEqual(bulk.completed, ['A'])
        self.assertIn('B', self.actual)

    def test_experimental_removal_and_nonbool_mode_rejected(self):
        self.tx.start('Test')
        self.assertEqual(self.tx.state, 'Failed')
        self.assertEqual(self.tasks, [])
        with self.assertRaisesRegex(ValueError, 'boolean'):
            UnlockTransaction(self.owner, self.submit, desired=0)


if __name__ == '__main__':
    unittest.main()
