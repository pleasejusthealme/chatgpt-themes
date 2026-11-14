import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_copy import SENTINEL, update_digest
from sumerki.build_patch import read_header, pack_header

class IntegrityTests(unittest.TestCase):
    def test_header_alignment_and_roundtrip(self):
        for n in range(8):
            header={'files': {'x'* (n+1): {'size':3,'offset':'0'}}}
            packed,raw=pack_header(header)
            parsed,base,original=read_header(io.BytesIO(packed+b'abc'))
            self.assertEqual(parsed,header)
            self.assertEqual(original,raw)
            self.assertEqual(packed.__len__(),base)
            self.assertEqual(base%4,0)

    def test_digest_slot_preserves_validation_and_surroundings(self):
        old,new=b'a'*32,b'b'*32
        data=b'prefix'+SENTINEL+b'\x01\x01'+old+b'suffix'
        patched=update_digest(data,old,new)
        self.assertEqual(patched,b'prefix'+SENTINEL+b'\x01\x01'+new+b'suffix')

    def test_unknown_or_ambiguous_build_fails_closed(self):
        slot=SENTINEL+b'\x01\x01'+b'a'*32
        for data in [b'none',slot+slot, SENTINEL+b'\x00\x01'+b'a'*32]:
            with self.assertRaises(ValueError):update_digest(data,b'a'*32,b'b'*32)

if __name__=='__main__':unittest.main()
