import unittest
from types import SimpleNamespace
from expedition33 import lease_policy as p, _lease_wire as wire
from expedition33._scope import SessionScope


class LeasePolicyTests(unittest.TestCase):
    def reply(self, **changes):
        values=dict(version=1,operation=2,limit=1024,quota=256,reserve=64,
                    error=0,active=130,peak=132,capacity=192,count=2,memory=7808)
        values.update(changes)
        return p.HEADER.pack(*values.values()) + p.OWNER.pack(0,0,0) + p.OWNER.pack(1,130,132) + bytes(62*p.OWNER.size)

    def test_accounting_and_growth(self):
        result=p.decode(p.request(2),self.reply())
        self.assertEqual((result['active'],result['capacity']),(130,192))
        self.assertEqual(result['owners'][1]['peak'],132)

    def test_malformed_accounting(self):
        for changes in (dict(limit=8193),dict(quota=0),dict(reserve=1024),dict(active=129),
                        dict(peak=129),dict(capacity=128),dict(count=65),dict(memory=0),dict(error=403)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                p.decode(p.request(2),self.reply(**changes))
        reply=bytearray(self.reply());reply[-1]=1
        with self.assertRaises(ValueError):p.decode(p.request(2),bytes(reply))

    def test_request_bounds(self):
        for args in ((1,127,1,0),(1,8193,1,0),(1,128,129,0),(1,128,1,128),(2,128,0,0)):
            with self.subTest(args=args),self.assertRaises(ValueError):p.request(*args)
        p.validate_request(p.request(1,1024,256,64))
        with self.assertRaises(ValueError):p.validate_request(self.reply())

    def test_negotiation_preserves_legacy_bound(self):
        sent=wire.request('lease-status')
        fields=list(wire.PACKET.unpack(sent));fields[2]=1;fields[3]=130
        encoded=wire.PACKET.pack(*fields).hex()
        with self.assertRaises(ValueError):wire.decode('lease-status',sent,encoded)
        self.assertEqual(wire.decode('lease-status',sent,encoded,capacity=1024).active,130)

    def test_subsystem_ids_survive_reload_and_context_errors(self):
        session=SimpleNamespace(_transport=SimpleNamespace(lease_policy_protocol=1,_lease_owner=0),_check=lambda:None)
        first=SessionScope(session,lease_owner='mod-a')
        reload=SessionScope(session,lease_owner='mod-a')
        other=SessionScope(session,lease_owner='mod-b')
        child=SessionScope(first)
        self.assertEqual(first._lease_owner_id,reload._lease_owner_id)
        self.assertEqual(child._lease_owner_id,first._lease_owner_id)
        with first._lease_context():
            try:
                with other._lease_context():
                    self.assertEqual(session._transport._lease_owner,other._lease_owner_id)
                    raise ValueError('test')
            except ValueError:pass
            self.assertEqual(session._transport._lease_owner,first._lease_owner_id)
        self.assertEqual(session._transport._lease_owner,0)
        for i in range(61):p.owner_id(session,f'extra-{i}')
        with self.assertRaises(RuntimeError):p.owner_id(session,'overflow')

    def test_uncertain_reply_aborts(self):
        aborted=[]
        session=SimpleNamespace(_check=lambda:None,_abort_ownership=lambda:aborted.append(True),
            _transport=SimpleNamespace(lease_policy_protocol=1,command=lambda *args:{'lease_policy_packet':'00'}))
        with self.assertRaises(ValueError):p.statistics(session)
        self.assertEqual(aborted,[True])

    def test_busy_configuration_preserves_session(self):
        def reject(command,packet):
            data=bytearray(packet);p.struct.pack_into('<I',data,20,403)
            return {'lease_policy_packet':data.hex()}
        aborted=[]
        session=SimpleNamespace(_check=lambda:None,_abort_ownership=lambda:aborted.append(True),
            _transport=SimpleNamespace(lease_policy_protocol=1,command=reject))
        with self.assertRaises(p.LeasePolicyRejected):p.configure(session)
        self.assertEqual(aborted,[])


if __name__=='__main__':unittest.main()
