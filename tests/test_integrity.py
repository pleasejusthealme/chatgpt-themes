import io
import base64
import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_copy import SENTINEL, update_digest
from sumerki.build_patch import read_header, pack_header, inject_document, manager_script, inject_profile_menu, PROFILE_CHILDREN

class IntegrityTests(unittest.TestCase):
    def test_native_menu_item_uses_native_component_after_settings(self):
        result=inject_profile_menu('prefix '+PROFILE_CHILDREN+' suffix')
        self.assertIn('_,N,(0,a.jsx)(H.tJ,',result)
        self.assertIn('children:"Темы"',result)
        self.assertIn('chatgpt-themes:open',result)
        with self.assertRaises(ValueError):inject_profile_menu(result)
        with self.assertRaises(ValueError):inject_profile_menu('unknown version')

    def test_manager_csp_authorizes_exact_script_only(self):
        script='(() => { window.test = "Привет"; })();'
        html='<html><head><meta http-equiv="Content-Security-Policy" content="script-src \'self\'; style-src \'self\' \'unsafe-inline\';"></head></html>'
        result=inject_document(html,'',script)
        digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn("script-src 'self' 'sha256-"+digest+"'",result)
        self.assertIn('>'+script+'</script>',result)
        self.assertNotIn("script-src 'self' 'unsafe-inline'",result)
        with self.assertRaises(ValueError):inject_document(result,'',script)

    def test_preset_data_cannot_close_script_tag(self):
        root=Path(__file__).resolve().parents[1]
        script=manager_script(root/'manager/manager.js','body{--x:"</script><script>"}')
        self.assertNotIn('</script',script.lower())
        self.assertNotIn('__THEME_PRESETS__',script)

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
