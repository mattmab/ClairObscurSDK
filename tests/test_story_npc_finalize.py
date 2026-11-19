import struct
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _story_npc_finalize_wire as wire
from expedition33.story_npc import StoryNpc
from expedition33._timeline_actor_channel import TimelineActorOwner

def obj(i):return N(index=i,serial=1000+i,address=i*0x10000)

def request(visual=True):
    objects=[obj(i) for i in range(1,9)]
    return wire.encode(99,*objects[:4],objects[4:],interaction=False,
        visual_owner=100 if visual else 0,visual=(9,1009,0x90000) if visual else None)

def ack(sent,*,error=0,completed=None,attempted=None):
    full=7 if struct.unpack_from('<I',sent,156)[0] else 5
    out=bytearray(sent);struct.pack_into('<II',out,8,error,0 if error else 1)
    struct.pack_into('<II',out,184,full if completed is None else completed,full if attempted is None else attempted)
    return bytes(out).hex()

class NpcFinalizeWireTests(unittest.TestCase):
    def test_full_success_and_strict_input_correlation(self):
        for visual,full in ((True,7),(False,5)):
            sent=request(visual);self.assertEqual(wire.decode(sent,ack(sent)),(full,full))
            for offset in (16,24,160,168):
                changed=bytearray.fromhex(ack(sent));changed[offset]^=1
                with self.assertRaises(ValueError):wire.decode(sent,changed.hex())
    def test_failed_prefix_is_exposed_without_authorizing_replay(self):
        sent=request()
        for completed,attempted in ((0,1),(1,3),(3,7),(7,7)):
            with self.assertRaises(wire.FinalizationError) as caught:
                wire.decode(sent,ack(sent,error=4341,completed=completed,attempted=attempted))
            self.assertEqual((caught.exception.completed,caught.exception.attempted),(completed,attempted))
            self.assertEqual(caught.exception.outcome,'unknown')
        with self.assertRaises(wire.FinalizationError) as caught:wire.decode(sent,ack(sent,error=4340,completed=0,attempted=0))
        self.assertEqual(caught.exception.outcome,'not_dispatched')
    def test_false_success_gaps_and_rejected_effects_fail_closed(self):
        sent=request()
        for error,completed,attempted in ((0,3,3),(4340,1,1),(4341,0,7),(4341,2,3),(4341,7,3)):
            with self.assertRaises(ValueError):wire.decode(sent,ack(sent,error=error,completed=completed,attempted=attempted))
    def test_duplicate_owner_and_unexpected_visual_or_tail_are_rejected(self):
        sent=request()
        for offset,value in ((160,99),(184,1),(1000,1)):
            changed=bytearray(sent);struct.pack_into('<I',changed,offset,value)
            with self.assertRaises(ValueError):wire.validate_request(bytes(changed))

class NpcFinalizeLifecycleTests(unittest.TestCase):
    def npc(self,*,visual=True,capability=1):
        npc=StoryNpc.__new__(StoryNpc);npc.state='prepared'
        transport=N(story_npc_finalize_protocol=capability)
        transport.command=Mock(side_effect=lambda _,sent:{'mesh_packet':ack(sent)})
        session=N(_transport=transport)
        scope=N(_session=session,_check=Mock(),_lease_context=nullcontext)
        npc.scope=scope
        def actor(index,token):
            owned=TimelineActorOwner.__new__(TimelineActorOwner)
            owned._owner=token;owned.phase='spawned';owned._timeline=True;owned._attempted=True
            return N(owner=owned,identity=(index,1000+index,index*0x10000),state='prepared',scope=scope,reveal=Mock(),close=Mock(return_value=True),retire_world=Mock(return_value=True))
        npc.actor=actor(1,99);npc.visual=actor(9,100) if visual else None
        npc.npc=obj(1);npc.dialogue_class=obj(2);npc.speaker=obj(3);npc.system_cdo=obj(4)
        npc.definitions=tuple(obj(i) for i in range(5,9));npc._configure=Mock()
        return npc,transport
    def test_public_npc_uses_one_handoff_and_remains_noninteractive_until_armed(self):
        npc,transport=self.npc();self.assertEqual(npc.reveal(interaction=False),npc.identity)
        transport.command.assert_called_once();npc._configure.assert_not_called();npc.actor.reveal.assert_not_called();npc.visual.reveal.assert_not_called()
        self.assertEqual((npc.state,npc.actor.state,npc.visual.state),('visible','visible','visible'))
        self.assertEqual((npc.actor.owner.phase,npc.visual.owner.phase),('visible','visible'))
        npc.set_interaction_enabled(False);transport.command.assert_called_once()
    def test_hidden_visual_is_excluded_and_stays_prepared(self):
        npc,transport=self.npc();npc.reveal(visual=False,interaction=False)
        self.assertEqual(npc.visual.state,'prepared');self.assertEqual(npc.visual.owner.phase,'spawned')
        self.assertEqual(struct.unpack_from('<I',transport.command.call_args.args[1],156)[0],0)
    def test_scope_or_owner_lifecycle_mismatch_rejects_before_native_command(self):
        for change in ('scope','phase','timeline','work'):
            npc,transport=self.npc()
            if change=='scope':npc.visual.scope=N(_check=Mock(),_session=object())
            elif change=='phase':npc.visual.owner.phase='visible'
            elif change=='timeline':npc.visual.owner._timeline=False
            else:npc.visual.owner._attempted=False
            with self.assertRaisesRegex(RuntimeError,'Prepared owned'):npc.reveal()
            transport.command.assert_not_called();self.assertEqual(npc.state,'failed')
    def test_partial_and_lost_ack_preserve_ownership_without_reveal_replay(self):
        for mode in ('prefix','lost','rejected'):
            npc,transport=self.npc()
            if mode=='lost':transport.command.side_effect=RuntimeError('lost reply')
            else:
                transport.command.side_effect=lambda _,sent:{'mesh_packet':ack(sent,error=4340 if mode=='rejected' else 4341,completed=0 if mode=='rejected' else 1,attempted=0 if mode=='rejected' else 3)}
            with self.assertRaises(RuntimeError):npc.reveal(interaction=False)
            with self.assertRaises(RuntimeError):npc.reveal(interaction=False)
            transport.command.assert_called_once();self.assertEqual(npc.state,'failed')
            if mode=='prefix':self.assertEqual((npc.actor.owner.phase,npc.visual.owner.phase),('visible','unknown'))
            elif mode=='lost':self.assertEqual((npc.actor.owner.phase,npc.visual.owner.phase),('unknown','unknown'))
            else:self.assertEqual((npc.actor.owner.phase,npc.visual.owner.phase),('spawned','spawned'))
            self.assertTrue(npc.actor.owner.has_native_work);self.assertTrue(npc.visual.owner.has_native_work)
            self.assertTrue(npc.close());npc.visual.close.assert_called_once();npc.actor.close.assert_called_once()
    def test_older_runtime_keeps_original_order_and_final_collision_gate(self):
        npc,transport=self.npc(capability=0);events=[]
        npc.actor.reveal.side_effect=lambda:events.append('carrier')
        npc.visual.reveal.side_effect=lambda:events.append('visual')
        npc._configure.side_effect=lambda active:events.append(('activate',active))
        with patch.object(npc,'set_interaction_enabled',side_effect=lambda enabled:events.append(('interaction',enabled))):
            npc.reveal(interaction=False)
        self.assertEqual(events,['carrier','visual',('activate',True),('interaction',False)])
        transport.command.assert_not_called()
    def test_presentation_only_carrier_does_not_repeat_collision_disable(self):
        npc,transport=self.npc();npc.reveal_presentation()
        self.assertFalse(npc._interaction_enabled);transport.command.assert_not_called();npc._configure.assert_not_called()

if __name__=='__main__':unittest.main()
