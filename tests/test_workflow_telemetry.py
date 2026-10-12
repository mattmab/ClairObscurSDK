import json
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import patch
from expedition33.workflow_telemetry import Telemetry

class TelemetryTests(unittest.TestCase):
    def test_poll_wait_is_separate_from_native_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            telemetry=Telemetry(Path(directory)/'events.jsonl')
            with patch('expedition33.workflow_telemetry.time.sleep') as sleep:
                telemetry.poll_wait(.005)
            sleep.assert_called_once_with(.005)
            telemetry.record('native.status','native_transport',time.time(),.001,True,ipc_round_trips=1)
            rows=telemetry.snapshot()['operations']
            self.assertEqual({r['category'] for r in rows},{'poll_wait','native_transport'})
            self.assertNotIn('ipc_round_trips',next(r for r in rows if r['category']=='poll_wait'))
            telemetry.close()
    def test_payloads_are_not_logged_and_rotation_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'events.jsonl'; telemetry=Telemetry(path)
            telemetry._handler.maxBytes=512
            for _ in range(20):
                telemetry.record('sdk.status','controller',time.time(),.001,True,
                    token='must-not-appear',arguments='must-not-appear',ipc_round_trips=1)
            telemetry.close()
            files=[file for file in Path(directory).glob('events.jsonl*')
                   if file != Path(str(path)+'.summary.json')]
            self.assertLessEqual(len(files),3)
            for file in files:
                text=file.read_text()
                self.assertNotIn('must-not-appear',text)
                for line in text.splitlines():
                    self.assertEqual(json.loads(line)['ipc_round_trips'],1)
            summary=json.loads(Path(str(path)+'.summary.json').read_text())
            self.assertEqual(summary['operations'][0]['count'],20)
            self.assertEqual(summary['operations'][0]['ipc_round_trips'],20)
            self.assertNotIn('must-not-appear',json.dumps(summary))

    def test_aggregate_cardinality_and_failure_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            telemetry=Telemetry(Path(directory)/'events.jsonl')
            for number in range(100):
                telemetry.record('op'+str(number),'test',time.time(),.001,number%2==0)
            snapshot=telemetry.snapshot()
            self.assertLessEqual(len(snapshot['operations']),64)
            self.assertEqual(sum(row['count'] for row in snapshot['operations']),100)
            self.assertEqual(sum(row['failures'] for row in snapshot['operations']),50)
            snapshot['operations'][0]['count']=10000
            self.assertEqual(sum(row['count'] for row in telemetry.snapshot()['operations']),100)
            telemetry.close()
