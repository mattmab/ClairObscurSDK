"""Ownership preparation crosses the reader/main boundary without a scope leak."""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS
from unittest.mock import patch
from expedition33.picto_inventory import PictoOwnership, prepare_ownership, STATIC_TABLE


class AffineScope:
    def __init__(self): self.thread = threading.get_ident()
    @property
    def pid(self):
        if threading.get_ident() != self.thread:
            raise RuntimeError('owner thread required')
        return 123


class PreparedOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.scope = AffineScope()
        self.obj = NS(object_flags=0)
        self.catalog = NS(objects=(self.obj,), path_name=lambda obj: STATIC_TABLE,
                          select=lambda cls: (self.obj,))
        self.snapshot = dict(pid=123, catalog=self.catalog, rows={'A': {'normal': True}},
                             table=self.obj, manager=self.obj, gi=self.obj, owned={})

    def test_prepare_worker_uses_pid_only_and_constructor_does_no_reads(self):
        with patch('expedition33.picto_inventory.discover_inventory', return_value=self.catalog), \
             patch('expedition33.picto_inventory.definitions', return_value={'A': {'normal': True}}), \
             patch('expedition33.picto_inventory.owned_pictos', return_value=(self.catalog, {})) as read:
            with ThreadPoolExecutor(max_workers=1) as worker:
                snapshot = worker.submit(prepare_ownership, self.scope.pid).result()
            self.assertEqual(read.call_count, 1)
            owner = PictoOwnership(self.scope, snapshot=snapshot)
            self.assertEqual(read.call_count, 1)
            with ThreadPoolExecutor(max_workers=1) as worker:
                self.assertEqual(worker.submit(owner.refresh).result(), {})
            self.assertEqual(read.call_count, 2)
            read.assert_called_with(123, catalog=self.catalog)

    def test_constructor_still_enforces_scope_owner(self):
        with ThreadPoolExecutor(max_workers=1) as worker:
            with self.assertRaisesRegex(RuntimeError, 'owner thread'):
                worker.submit(PictoOwnership, self.scope, snapshot=self.snapshot).result()

    def test_rejects_other_process_without_reading(self):
        self.snapshot['pid'] = 456
        with patch('expedition33.picto_inventory.owned_pictos') as read:
            with self.assertRaisesRegex(ValueError, 'different process'):
                PictoOwnership(self.scope, snapshot=self.snapshot)
            read.assert_not_called()

    def test_default_constructor_retains_one_authoritative_read(self):
        with patch('expedition33.picto_inventory.prepare_ownership', return_value=self.snapshot) as prepare:
            owner = PictoOwnership(self.scope, self.catalog)
            prepare.assert_called_once_with(123, self.catalog)
            self.assertEqual(owner.pid, 123)
            owner.rows['A']['normal'] = False
            self.assertTrue(self.snapshot['rows']['A']['normal'])


if __name__ == '__main__': unittest.main()
