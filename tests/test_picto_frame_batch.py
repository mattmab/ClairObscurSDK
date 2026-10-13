import unittest
from concurrent.futures import Future
from types import SimpleNamespace as NS
from unittest.mock import Mock
from unittest.mock import patch
from expedition33.picto_batch import FrameBulkTransaction, HEADER, ENTRY, SIZE, validate_request
from expedition33.picto_transactions import UnlockTransaction

def ready(value):
    f=Future();f.set_result(value);return f

class FrameBatchTests(unittest.TestCase):
    def test_startup_subset_cannot_change_unrequested_items(self):
        self.level_job()
        tx=UnlockTransaction(self.owner,lambda fn:ready(fn()))
        job=FrameBulkTransaction(tx,level=(32,self.owner.manager,self.owner.function()),identities=['B'])
        job.start();job.poll()
        self.assertEqual(job.ids,['B']);self.assertEqual(HEADER.unpack_from(self.packet)[5],1)
        for ids in (['A','A'],['Missing']):
            with self.assertRaises(ValueError):FrameBulkTransaction(tx,level=(32,self.owner.manager,self.owner.function()),identities=ids)

    def level_job(self,level=32):
        self.setup_job()
        self.owner.owned={key:(NS(index=40+i,serial=1,address=(40+i)*16),33) for i,key in enumerate(('A','B','C'))}
        tx=UnlockTransaction(self.owner,lambda fn:ready(fn()))
        return FrameBulkTransaction(tx,level=(level,self.owner.manager,self.owner.function()))

    def test_level_batch_submits_owned_items_and_verifies_each_level(self):
        job=self.level_job();job.start();job.poll()
        self.assertEqual(HEADER.unpack_from(self.packet)[6],2)
        self.assertEqual(HEADER.unpack_from(self.packet)[8],32)
        for i,key in enumerate(('A','B','C')):
            self.assertEqual(ENTRY.unpack_from(self.packet,104+i*32)[0],40+i)
        self.packet[12:16]=(2).to_bytes(4,'little');self.packet[32:36]=(3).to_bytes(4,'little')
        for i,key in enumerate(('A','B','C')):
            obj,_=self.owner.owned[key];self.owner.owned[key]=(obj,33 if key=='B' else 32)
            ENTRY.pack_into(self.packet,104+i*32,obj.index,obj.serial,obj.address,1777 if key=='B' else 0,1,100+i)
        job.poll();job.poll()
        self.assertEqual(job.completed,['A','C']);self.assertIn('B',job.failed)
        self.assertEqual(self.owner.refresh.call_count,2);self.assertEqual(self.starts,1)

    def test_level_preflight_skips_matching_levels_and_removed_items(self):
        job=self.level_job();obj,_=self.owner.owned['A'];self.owner.owned['A']=(obj,32)
        self.owner.owned.pop('B');job.start();job.poll()
        self.assertEqual(job.skipped,['A']);self.assertEqual(job.ids,['C']);self.assertIn('B',job.failed)

    def test_level_cancel_keeps_only_confirmed_attempts(self):
        job=self.level_job();job.start();job.poll()
        obj,_=self.owner.owned['A'];self.owner.owned['A']=(obj,32)
        self.packet[32:36]=(1).to_bytes(4,'little')
        ENTRY.pack_into(self.packet,104,obj.index,obj.serial,obj.address,0,1,100)
        job.stop();job.poll()
        self.assertEqual(job.completed,['A']);self.assertTrue(job.done)

    def test_level_bounds_are_checked_before_dispatch(self):
        self.setup_job()
        for value in (0,34,True,1.5):
            with self.assertRaises(ValueError):FrameBulkTransaction(UnlockTransaction(self.owner,lambda fn:ready(fn())),level=(value,None,None))

    def mastery_job(self,mastered):
        self.level_job()
        tx=UnlockTransaction(self.owner,lambda fn:ready(fn()))
        job=FrameBulkTransaction(tx,mastery=(mastered,self.owner.manager,self.owner.function(),self.owner.table))
        self.progress={key:(2,False) for key in self.owner.owned}
        def refresh():return self.owner.refresh(),dict(self.progress)
        job._refresh=refresh
        return job

    def finish_mastery(self,job,processed=3):
        self.packet[12:16]=(2).to_bytes(4,'little');self.packet[32:36]=processed.to_bytes(4,'little')
        for i,key in enumerate(job.ids[:processed]):
            obj,_=self.owner.owned[key]
            ENTRY.pack_into(self.packet,104+i*32,obj.index,obj.serial,obj.address,0,1,100+i)

    def test_master_and_unmaster_share_single_submission_and_final_read(self):
        for mastered in (True,False):
            with self.subTest(mastered=mastered):
                job=self.mastery_job(mastered);job.start();job.poll()
                self.assertEqual(HEADER.unpack_from(self.packet)[6],3)
                self.assertEqual(HEADER.unpack_from(self.packet)[8],int(mastered))
                for i in range(3):self.assertEqual(ENTRY.unpack_from(self.packet,104+i*32)[0],40+i)
                self.progress={key:((4,True) if mastered else (0,False)) for key in self.owner.owned}
                self.finish_mastery(job);job.poll();job.poll()
                self.assertEqual(job.completed,['A','B','C']);self.assertFalse(job.failed)
                self.assertEqual(self.owner.refresh.call_count,2);self.assertEqual(self.starts,1)

    def test_unmaster_resets_partial_progress_but_skips_zero(self):
        job=self.mastery_job(False);self.progress['A']=(0,False);self.owner.owned.pop('B')
        job.start();job.poll()
        self.assertEqual(job.skipped,['A']);self.assertEqual(job.ids,['C']);self.assertIn('B',job.failed)
        self.finish_mastery(job,1);job.poll();job.poll()
        self.assertFalse(job.completed);self.assertIn('C',job.failed)

    def test_master_does_not_accept_count_without_learnt_flag(self):
        job=self.mastery_job(True);job.start();job.poll();self.progress['A']=(4,False)
        self.finish_mastery(job);job.poll();job.poll()
        self.assertFalse(job.completed);self.assertEqual(len(job.failed),3)

    def test_cancel_mastery_only_saves_confirmed_attempts(self):
        job=self.mastery_job(False);job.start();job.poll()
        self.progress['A']=(0,False);self.finish_mastery(job,1)
        job.stop();job.poll()
        self.assertEqual(job.completed,['A']);self.assertTrue(job.done);self.assertEqual(self.starts,1)

    def test_mastery_requires_boolean_and_excludes_level_mode(self):
        self.level_job();tx=UnlockTransaction(self.owner,lambda fn:ready(fn()))
        for value in (0,1,None,'false'):
            with self.assertRaises(ValueError):FrameBulkTransaction(tx,mastery=(value,None,None,None))
        with self.assertRaises(ValueError):FrameBulkTransaction(tx,level=(33,None,None),mastery=(True,None,None,None))
        job=self.mastery_job(True);job.start();job.poll()
        bad=bytearray(job.request);bad[36:40]=(2).to_bytes(4,'little')
        with self.assertRaises(ValueError):validate_request(bytes(bad))

    def test_inventory_refresh_discards_recycled_object_catalog(self):
        from expedition33.picto_inventory import PictoOwnership
        owner=object.__new__(PictoOwnership);owner.pid=123;owner.catalog=object()
        fresh=object();observed=object()
        with patch('expedition33.picto_inventory.discover_inventory',return_value=fresh) as discover, patch('expedition33.picto_inventory.owned_pictos',return_value=(observed,{'A':1})) as read:
            self.assertEqual(owner.refresh(),{'A':1})
            discover.assert_called_once_with(123);read.assert_called_once_with(123,catalog=fresh)
            self.assertIs(owner.catalog,observed)

    def setup_job(self,desired=False):
        obj=lambda i:NS(index=i,serial=1,address=i*16)
        transport=Mock();scope=NS(_check=Mock(),_session=NS(_transport=transport))
        owner=NS(scope=scope,manager=obj(1),table=obj(2),gi=obj(3),function=Mock(return_value=obj(4)),
                 rows={k:dict(normal=True,asset=obj(i)) for i,k in enumerate(('A','B','C'),10)},owned={} if desired else dict.fromkeys(('A','B','C'),1))
        owner.refresh=Mock(side_effect=lambda:dict(owner.owned))
        tx=UnlockTransaction(owner,lambda fn:ready(fn()),desired=desired)
        job=FrameBulkTransaction(tx);self.owner=owner;self.transport=transport
        self.packet=None;self.starts=0
        def command(name,data):
            validate_request(data);op=HEADER.unpack_from(data)[1]
            if op==1:
                self.starts+=1;self.packet=bytearray(data);self.packet[12:16]=(1).to_bytes(4,'little')
            result=bytearray(self.packet);result[4:8]=op.to_bytes(4,'little')
            if op==3:result[12:16]=(3).to_bytes(4,'little');self.packet=result
            return {'picto_batch_packet':result.hex()}
        transport.command.side_effect=command
        return job

    def complete(self,processed=3,protected=None):
        self.packet[12:16]=(2).to_bytes(4,'little');self.packet[32:36]=processed.to_bytes(4,'little')
        for i,key in enumerate(('A','B','C')[:processed]):
            offset=104+i*32;index,serial,address,_,_,_=ENTRY.unpack_from(self.packet,offset)
            ENTRY.pack_into(self.packet,offset,index,serial,address,1759 if key==protected else 0,0 if key==protected else 1,100+i)
            if key!=protected:
                if HEADER.unpack_from(self.packet)[6]:self.owner.owned[key]=1
                else:self.owner.owned.pop(key,None)

    def test_single_submission_and_single_final_read_protected_continues(self):
        job=self.setup_job();job.start();job.poll()
        self.assertEqual(self.starts,1);self.assertEqual(self.owner.refresh.call_count,1)
        job.poll();job.poll();self.assertEqual(self.owner.refresh.call_count,1)
        self.complete(protected='B');job.poll();job.poll()
        self.assertTrue(job.done);self.assertEqual(job.completed,['A','C'])
        self.assertEqual(job.failed,{'B':'Equipped Picto protected'})
        self.assertEqual(self.owner.refresh.call_count,2);self.assertEqual(job.frames,[100,101,102])

    def test_add_and_cancel_only_records_attempted(self):
        job=self.setup_job(True);job.start();job.poll();self.complete(1)
        job.stop();job.poll()
        self.assertTrue(job.done);self.assertEqual(job.completed,['A']);self.assertEqual(self.starts,1)

    def test_cancel_before_dispatch(self):
        job=self.setup_job();job.start();job.stop();job.poll()
        self.assertTrue(job.done);self.assertEqual(self.starts,0)

    def test_lost_start_reply_is_cancelled_not_resubmitted(self):
        job=self.setup_job();original=self.transport.command.side_effect
        def lost(name,data):
            result=original(name,data)
            if HEADER.unpack_from(data)[1]==1:raise TimeoutError('lost reply')
            return result
        self.transport.command.side_effect=lost
        job.start();job.poll();job.poll()
        self.assertTrue(job.done);self.assertEqual(self.starts,1);self.assertIn('lost reply',job.error)

    def test_same_frame_reply_is_rejected(self):
        job=self.setup_job();job.start();job.poll();self.complete()
        self.packet[104+32+24:104+32+32]=(100).to_bytes(8,'little')
        job.poll();job.poll();self.assertIn('frame order',job.error);self.assertEqual(self.starts,1)

    def test_packet_bounds_and_dirty_query(self):
        data=HEADER.pack(1,2,0,0,1,0,0,0,0)+bytes(SIZE-40)
        validate_request(data)
        for bad in (data[:-1],data[:24]+(343).to_bytes(4,'little')+data[28:],data[:-1]+b'\x01'):
            with self.assertRaises(ValueError):validate_request(bad)

if __name__=='__main__':unittest.main()
