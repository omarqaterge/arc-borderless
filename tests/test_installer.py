import importlib.util
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('borderless',Path(__file__).resolve().parents[1]/'borderless.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self): self.tmp.cleanup()
 def test_atomic_manifest(self):
  path=self.root/'state/manifest.json';b.atomic_json(path,{'v':1});b.atomic_json(path,{'v':2})
  self.assertEqual(json.loads(path.read_text()),{'v':2});self.assertFalse(path.with_name('manifest.json.tmp').exists())
 def test_copy_does_not_share_writes(self):
  source=self.root/'source';source.mkdir();(source/'value').write_text('old')
  b.clone(source,self.root/'copy');(self.root/'copy/value').write_text('new')
  self.assertEqual((source/'value').read_text(),'old')
 def test_refuses_existing_destination(self):
  source=self.root/'source';source.mkdir()
  with self.assertRaises(b.Failure):b.clone(source,source)
 def test_signed_launcher_uses_official_arc_and_normal_profile(self):
  source=(Path(__file__).resolve().parents[1]/'src/Launcher.m').read_text()
  self.assertIn('signed-single-instance',source);self.assertIn('ARCB_OFFICIAL_MODE',source)
  self.assertIn('quitOfficialArc()',source);self.assertIn('if(probe)',source)
  self.assertNotIn('CFFIXED_USER_HOME",',source.split('if(probe)')[0])
  self.assertIn('unsetenv("CFFIXED_USER_HOME")',source)
 def test_launcher_rejects_changed_arc_binary(self):
  source=(Path(__file__).resolve().parents[1]/'src/Launcher.m').read_text()
  self.assertIn('fileSHA256(binary)',source)
  self.assertIn('Arc Borderless needs an update',source)
 def test_patch_does_not_replace_keychain_cloud_or_updater(self):
  sources='\n'.join((Path(__file__).resolve().parents[1]/name).read_text() for name in ['src/OfficialBorderless.m','src/Runtime.inc'])
  self.assertNotIn('SecItem',sources);self.assertNotIn('CKContainer',sources)
  self.assertNotIn('installUpdateBlock',sources)
 def fake_tools(self):
  tools=self.root/'tools';tools.mkdir(exist_ok=True);(tools/'launcher').write_text('launcher');return tools
 def test_build_creates_launcher_instead_of_copying_arc(self):
  source=self.root/'Arc.app';(source/'Contents/Resources').mkdir(parents=True);(source/'Contents/Resources/AppIcon.icns').write_text('icon')
  target=self.root/'Arc Borderless.app';calls=[]
  def fake_run(*args,**kwargs): calls.append(tuple(map(str,args)));return SimpleNamespace()
  info={'version':'1','build':'2','sourceSHA256':'abc','source':str(source),'staticCompatible':True}
  with patch.object(b,'preflight',return_value=info),patch.object(b,'build_tools',side_effect=self.fake_tools),patch.object(b,'run',side_effect=fake_run):
   cfg=b.build_app(source,target)
  app_info=plistlib.loads((target/'Contents/Info.plist').read_bytes())
  self.assertEqual(cfg['mode'],'signed-single-instance');self.assertEqual(app_info['CFBundleIdentifier'],b.SIGNED_BUNDLE_ID)
  self.assertFalse((target/'Contents/MacOS/Arc').exists())
  self.assertTrue(any('OfficialBorderless.m' in part for call in calls for part in call))
 def install_fixture(self):
  app=self.root/'Applications/Arc Borderless.app';app.mkdir(parents=True);(app/'old').write_text('old')
  source=self.root/'Applications/Arc.app';source.mkdir(parents=True)
  state=self.root/'Library/Arc Borderless';(state/'home').mkdir(parents=True)
  return SimpleNamespace(app=app,source=source,state=state)
 def fake_build(self,source,target):
  (target/'Contents/Resources').mkdir(parents=True);(target/'new').write_text('new')
  cfg={'mode':'signed-single-instance','formatVersion':2,'sourceInfo':{'source':str(source),'build':'2'}}
  (target/'Contents/Resources/Borderless.plist').write_bytes(plistlib.dumps(cfg));return cfg
 def test_failed_validation_keeps_existing_app(self):
  args=self.install_fixture()
  with patch.object(b,'build_app',side_effect=self.fake_build),patch.object(b,'quit_app'),patch.object(b,'validate',side_effect=b.Failure('failed')):
   with self.assertRaises(b.Failure):b.install(args)
  self.assertEqual((args.app/'old').read_text(),'old')
 def test_successful_install_backs_up_app_and_retains_legacy_profile(self):
  args=self.install_fixture()
  with patch.object(b,'build_app',side_effect=self.fake_build),patch.object(b,'quit_app'),patch.object(b,'validate',return_value={'hooksInstalled':True}):b.install(args)
  self.assertTrue((args.app/'new').exists());self.assertTrue((args.state/'home').exists())
  manifest=json.loads((args.state/'signed-installation.json').read_text());backup=Path(manifest['previousAppBackup'])
  self.assertEqual((backup/'Arc Borderless.app/old').read_text(),'old');self.assertTrue(manifest['legacyProfileRetained'])

if __name__=='__main__':unittest.main()
