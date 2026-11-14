import contextlib
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gui_backend as backend
from sumerki.build_patch import inject_document, inject_profile_menu, PROFILE_CHILDREN

class RepatchTests(unittest.TestCase):
    def test_replace_known_manager_without_accumulating_scripts_or_hashes(self):
        html='<head><meta content="script-src \'self\'; style-src \'self\' \'unsafe-inline\';"></head>'
        old=inject_document(html,'','window.old=true;')
        new=inject_document(old,'','window.new=true;',allow_repatch=True)
        self.assertNotIn('window.old=true',new)
        self.assertEqual(new.count('id="chatgpt-themes-manager-script"'),1)
        self.assertEqual(new.count("'sha256-"),1)
        self.assertEqual(inject_profile_menu(inject_profile_menu(PROFILE_CHILDREN),True),inject_profile_menu(PROFILE_CHILDREN))
    def test_refuse_unknown_old_manager_hash(self):
        html='<head><meta content="script-src \'self\';"></head>'
        old=inject_document(html,'','old()').replace('old()','tampered()')
        with self.assertRaises(ValueError):inject_document(old,'','new()',True)

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=self.root/'Applications/ChatGPT.app';self.state=self.root/'state'
        (self.app/'Contents/Resources').mkdir(parents=True)
        self.info={'CFBundleIdentifier':'com.openai.codex','CFBundleVersion':'27194','CFBundleShortVersionString':'26.1111.21308','ElectronAsarIntegrity':{'Resources/app.asar':{'algorithm':'SHA256','hash':'old'}}}
        (self.app/'Contents/Info.plist').write_bytes(plistlib.dumps(self.info))
        (self.app/'Contents/Resources/app.asar').write_bytes(b'current')
    def tearDown(self):self.tmp.cleanup()
    def build(self,source,css,out,**kwargs):
        self.assertTrue(kwargs['allow_repatch'])
        (out/'app.asar').write_bytes(b'new manager')
        (out/'Info.plist').write_bytes(plistlib.dumps(self.info))
    def test_apply_update_and_restore_preserve_first_backup(self):
        with patch.object(backend,'verify'),patch.object(backend,'assert_closed'),patch.object(backend,'clone',side_effect=shutil.copytree),patch.object(backend,'build',side_effect=self.build),patch.object(backend,'patch_framework'),patch.object(backend,'run'),contextlib.redirect_stdout(io.StringIO()):
            backend.operate('apply',self.app,self.state)
            self.assertEqual((self.app/'Contents/Resources/app.asar').read_bytes(),b'new manager')
            first=backend.read_record(backend.record_path(self.state,self.app))['baseline']
            backend.operate('apply',self.app,self.state)
            self.assertEqual(backend.read_record(backend.record_path(self.state,self.app))['baseline'],first)
            backend.operate('restore',self.app,self.state)
            self.assertEqual((self.app/'Contents/Resources/app.asar').read_bytes(),b'current')
            self.assertEqual(len(backend.read_record(backend.record_path(self.state,self.app))['history']),3)
    def test_atomic_replace_failure_restores_installed_app(self):
        stage=self.app.parent/'stage.app';stage.mkdir();park=self.app.parent/'park.app'
        original=os.rename
        def rename(source,target):
            if source==stage:raise OSError('simulated failure')
            return original(source,target)
        with patch.object(backend.os,'rename',side_effect=rename):
            with self.assertRaises(OSError):backend.atomic_swap(self.app,stage,park)
        self.assertTrue(self.app.exists());self.assertFalse(park.exists())
    def test_running_app_refusal_precedes_copy(self):
        with patch.object(backend,'assert_closed',side_effect=backend.PatcherError('running')),patch.object(backend,'clone') as clone:
            with self.assertRaises(backend.PatcherError):backend.operate('apply',self.app,self.state)
            clone.assert_not_called()
        self.assertFalse(backend.record_path(self.state,self.app).exists())

if __name__=='__main__':unittest.main()
