"""Synthetic FC3000 notification-audit tests; no real identifiers."""
import struct
import unittest

from scripts.fc3000_legacy_notify_audit import att_records, summarize


def att_frame(op, handle, payload, second):
    att = bytes([op]) + struct.pack("<H", handle) + payload
    l2 = struct.pack("<HH", len(att), 4) + att
    acl = struct.pack("<HH", 0x2001, len(l2)) + l2
    frame = struct.pack(">I", 0) + b"\x02" + acl
    return struct.pack(">IIII", second, 0, len(frame), len(frame)) + frame


class NotifyAuditTests(unittest.TestCase):
    def test_nearby_does_not_mean_ack(self):
        rows = [
            (100.0, 0x12, 0x002d, b"1|0|session|FC0123456789|1"),
            (101.0, 0x1b, 0x002a, b"periodic"),
            (103.0, 0x1b, 0x002a, b"late"),
        ]
        result = summarize(rows)
        self.assertEqual(result["commands"], 1)
        self.assertEqual(result["events"][0]["notify_within_2s"], 1)
        self.assertFalse(result["events"][0]["ack_verified"])

    def test_pcap_parsing(self):
        b = (struct.pack(">IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 2048, 201)
             + att_frame(0x12, 0x002d, b"1|0|session|FC0123456789|0", 100)
             + att_frame(0x1b, 0x002a, b"x", 101))
        result = summarize(att_records(b))
        self.assertEqual(result["commands"], 1)
        self.assertEqual(result["notifications"], 1)
        self.assertEqual(result["events"][0]["notify_within_2s"], 1)

    def test_truncation_rejected(self):
        with self.assertRaises(ValueError):
            att_records(b"\xa1\xb2")


if __name__ == "__main__":
    unittest.main()
