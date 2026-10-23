import unittest
from types import SimpleNamespace
from expedition33._enemy_spawn_wire import build_request, validate_request, OPERATIONS


class EnemyRequestBuilderTests(unittest.TestCase):
    def identities(self, count):
        return tuple(SimpleNamespace(index=i+1, serial=i+2, address=0x10000+i*256) for i in range(count))

    def test_every_operation_produces_canonical_request(self):
        for operation, count in OPERATIONS.items():
            with self.subTest(operation=operation):
                pose=(0,0,0,1,100,200,300,0,1,1,1,0) if operation in (110,120,133) else (0,0,100,50,50,50) if operation==119 else (100,200,300) if operation==123 else ()
                options={'total_count':10} if operation==122 else {'authored_route':1} if operation==133 else {}
                self.assertTrue(validate_request(build_request(123, operation, self.identities(count), pose, int(operation==112), **options)))

    def test_ignored_inputs_are_rejected(self):
        for args in ((123,111,self.identities(1)), (123,111,(),(0,)), (123,111,(),(),1), (123,112,self.identities(2),(),2), (True,111), (123,True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                build_request(*args)

    def test_invalid_identities_and_transforms_are_rejected(self):
        for identity in (SimpleNamespace(index=-1,serial=1,address=0x10000), SimpleNamespace(index=True,serial=1,address=0x10000), SimpleNamespace(index=1,serial=1,address=2**64), object()):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                build_request(123,113,(identity,))
        for pose in ((0,0,0,1,float('nan'),0,0,0,1,1,1,0), (0,0,0,1,0,0,0,0,2,1,1,0)):
            with self.assertRaises(ValueError):build_request(123,110,self.identities(12),pose)
