from contextlib import nullcontext
from types import SimpleNamespace as N
import threading
import unittest
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33 import console_startup as m


def catalog():
    names=(('Console','Class','/Script/Engine.Console'),
        ('GameplayStatics','Class','/Script/Engine.GameplayStatics'),
        ('Default__GameplayStatics','GameplayStatics','/Script/Engine.Default__GameplayStatics'),
        ('SpawnObject','Function','/Script/Engine.GameplayStatics:SpawnObject'),
        ('Viewport','CustomGameViewportClient','/Engine/Transient.Viewport'))
    objects=[N(index=i,serial=3,address=4096+i*128,name=name,class_name=cls,path=path,
        object_flags=0x10 if i==2 else 0,class_index=1 if i==2 else 6,
        outer_index=1 if i==3 else -1,outer_serial=3 if i==3 else 0)
        for i,(name,cls,path) in enumerate(names)]
    return N(pid=7,objects=objects,path_name=lambda obj:obj.path)


class ConsoleStartupTests(unittest.TestCase):
    def run_observer(self, first=None, second=None, values=None, error=None):
        first=first or catalog();second=second or first
        reader=N(bind=nullcontext,close=Mock())
        if values is None:values=[None,None]
        def read(cat,objects,**kwargs):
            value=values.pop(0);key=(9,'ViewportConsole')
            return {4:N(types={key:'ObjectProperty'},values={key:value},errors={},truncated=set())}
        with patch.object(m,'ReadBatch',return_value=reader), \
                patch.object(m,'capture_matching',return_value=first,side_effect=error) as discover, \
                patch.object(m,'capture_selected',return_value=second) as selected, \
                patch.object(m,'read_values_many',side_effect=read):
            observer=m.ConsolePrerequisiteObserver(7)
            result=observer.observe()
        return result,observer,reader,discover,selected

    def test_ready_without_world_controller_player_or_title(self):
        result,observer,reader,discover,selected=self.run_observer()
        self.assertIs(result,True)
        self.assertEqual(selected.call_count,1)
        self.assertEqual(discover.call_args.kwargs['classes'],('CustomGameViewportClient',))
        observer.close();reader.close.assert_called_once_with()

    def test_missing_viewport_and_ambiguous_viewport_reject(self):
        for change in ('missing','ambiguous'):
            cat=catalog()
            if change=='missing':cat.objects.pop()
            else:cat.objects.append(N(**vars(cat.objects[-1])))
            result,_,_,_,selected=self.run_observer(first=cat)
            self.assertIs(result,False);selected.assert_not_called()

    def test_occupied_slot_never_authorizes_attach(self):
        result,_,_,_,selected=self.run_observer(values=[object()])
        self.assertIs(result,False);selected.assert_not_called()
        result,*_=self.run_observer(values=[None,object()])
        self.assertIs(result,False)

    def test_identity_changes_and_transient_errors_are_uncertain(self):
        cat=catalog();cat.objects[-1].serial+=1
        result,*_=self.run_observer(second=cat)
        self.assertIsNone(result)
        result,observer,reader,_,_=self.run_observer(error=RuntimeQueryError('READ_FAILED'))
        self.assertIsNone(result);reader.close.assert_called_once_with()
        self.assertIsNone(observer._reader)

    def test_unknown_decoder_error_propagates_and_closes_reader(self):
        with self.assertRaisesRegex(RuntimeQueryError,'UNKNOWN_SCHEMA'):
            self.run_observer(error=RuntimeQueryError('UNKNOWN_SCHEMA'))

    def test_wrong_function_owner_and_class_paths_reject(self):
        for index in (0,1,2,3):
            cat=catalog();cat.objects[index].path='other'
            result,*_=self.run_observer(first=cat)
            self.assertIs(result,False)

    def test_worker_affinity(self):
        observer=m.ConsolePrerequisiteObserver(7);errors=[]
        def run():
            try:observer.observe()
            except RuntimeError as error:errors.append(error)
        thread=threading.Thread(target=run);thread.start();thread.join()
        self.assertEqual(len(errors),1)


if __name__=='__main__':unittest.main()
