"""Offline decoder fixture tests; no real device or secrets required."""
import struct
import unittest

from scripts.fc3000_legacy_pcap_decode import decode_mars_legacy, parse_pcap


def synthetic_pcap(payload: bytes, handle: int = 0x002d) -> bytes:
    att = bytes([0x12]) + struct.pack("<H", handle) + payload
    l2 = struct.pack("<HH", len(att), 4) + att
    acl = struct.pack("<HH", 0x2001, len(l2)) + l2
    frame = struct.pack(">I", 0) + b"\x02" + acl
    header = struct.pack(">IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 2048, 201)
    packet = struct.pack(">IIII", 1794500000, 123456, len(frame), len(frame)) + frame
    return header + packet


class FC3000PcapTests(unittest.TestCase):
    def test_on_off(self):
        self.assertEqual(decode_mars_legacy(b"1|0|12345|FC0123456789|1")["action"], "light_on")
        self.assertEqual(decode_mars_legacy(b"1|0|12345|FC0123456789|0")["action"], "light_off")

    def test_brightness_candidate(self):
        row = decode_mars_legacy(b"2|0|12345|FC0123456789|75")
        self.assertEqual(row["value"], 75)
        self.assertFalse(row["verified_replay"])
        self.assertNotIn("12345", str(row))
        self.assertNotIn("FC0123456789", str(row))

    def test_invalid_rejected(self):
        self.assertIsNone(decode_mars_legacy(b"2|0|12345|FC0123456789|101"))
        self.assertIsNone(decode_mars_legacy(b"1|0|12345|FC0123456789|2"))
        self.assertIsNone(decode_mars_legacy(b"2|0|12345|FC0123456789|-1"))

    def test_parse_valid_capture(self):
        output = parse_pcap(synthetic_pcap(b"2|0|12345|FC0123456789|50"))
        self.assertEqual(output["total_hci_packets"], 1)
        self.assertEqual(output["fc3000_candidate_writes"], 1)
        self.assertEqual(output["events"][0]["value"], 50)

    def test_wrong_handle_not_reported(self):
        output = parse_pcap(synthetic_pcap(b"2|0|12345|FC0123456789|50", 0x0030))
        self.assertEqual(output["fc3000_candidate_writes"], 0)

    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):
            parse_pcap(synthetic_pcap(b"2|0|12345|FC0123456789|50")[:-1])


if __name__ == "__main__":
    unittest.main()
