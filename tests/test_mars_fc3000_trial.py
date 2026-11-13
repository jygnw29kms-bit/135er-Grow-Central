"""FC3000 owner-only hardware trial protocol: dry-run contract tests.

Never sends device commands or opens Bluetooth connections.
"""
import unittest
from app.mars_fc3000_trial import context_from_live_status, encode_command

def sample(*,state="1",brightness="50",code="68756",version="3.4"):
    fields=["0","opaque","", "MARS",version,code,"1","0","","","-1","",
            state,brightness,"0","0","timestamp","97496","0"]
    return ("|".join(fields)+chr(10)).encode("ascii")

class TestFc3000Trial(unittest.TestCase):
    def test_extract_fresh_status_code_without_leaking(self):
        ctx=context_from_live_status(sample(brightness="76"))
        self.assertIsNotNone(ctx)
        code,status=ctx
        self.assertEqual(len(code),5)
        self.assertTrue(status["power_on"])
        self.assertEqual(status["brightness_percent"],76)
        self.assertNotIn(code,str(status))

    def test_exact_original_app_packet_structure(self):
        self.assertEqual(
            encode_command(code="68756",device_id="FCB467AEC260",
                           action="brightness",value=50),
            b"2|0|68756|FCB467AEC260|50")
        self.assertEqual(
            encode_command(code="68756",device_id="FCB467AEC260",
                           action="power",value=0),
            b"1|0|68756|FCB467AEC260|0")

    def test_refuse_guesses_and_unsafe_values(self):
        cases=[
            dict(code="wrong",device_id="FCB467AEC260",action="power",value=1),
            dict(code="68756",device_id="WRONG",action="power",value=1),
            dict(code="68756",device_id="FCB467AEC260",action="power",value=2),
            dict(code="68756",device_id="FCB467AEC260",action="brightness",value=0),
            dict(code="68756",device_id="FCB467AEC260",action="brightness",value=101),
            dict(code="68756",device_id="FCB467AEC260",action="brightness",value=True),
            dict(code="68756",device_id="FCB467AEC260",action="temperature",value=30),
        ]
        for kw in cases:
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                encode_command(**kw)

    def test_reject_other_firmware_or_fan(self):
        self.assertIsNone(context_from_live_status(sample(version="3.5")))
        self.assertIsNone(context_from_live_status(sample(code="wrong")))
        self.assertIsNone(context_from_live_status(sample().replace(b"MARS",b"FANX")))

if __name__=="__main__":
    unittest.main()
