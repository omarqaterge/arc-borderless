import importlib.util
import json
from pathlib import Path
import plistlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('borderless',Path(__file__).resolve().parents[1]/'borderless.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self): self.tmp.cleanup()
 def source(self):
  p=self.root/'source';(p/'User Data/Default').mkdir(parents=True)
  (p/'StorableSidebar.json').write_text(json.dumps({'spaces':['a'],'items':['x']}))
  db=sqlite3.connect(p/'User Data/Default/Cookies')
  db.execute('CREATE TABLE cookies (host_key TEXT)');db.execute('INSERT INTO cookies VALUES (?)',('example.test',));db.commit();db.close()
  (p/'User Data/SingletonLock').symlink_to('/unavailable/pid')
  return p
 def test_snapshot_copies_sidebar_and_database_and_drops_stale_lock(self):
  src=self.source();stats=b.prepare_profile(self.root/'copy',src)
  self.assertEqual(stats['profiles']['Default']['Cookies'],1)
  self.assertEqual((src/'StorableSidebar.json').read_bytes(),(b.data_dir(self.root/'copy')/'StorableSidebar.json').read_bytes())
  self.assertFalse((b.data_dir(self.root/'copy')/'User Data/SingletonLock').is_symlink())
  self.assertTrue((src/'User Data/SingletonLock').is_symlink())
 def test_copy_does_not_share_writes(self):
  src=self.source();b.clone(src,self.root/'copy')
  (self.root/'copy/StorableSidebar.json').write_text('{}')
  self.assertNotEqual((src/'StorableSidebar.json').read_text(),'{}')
 def test_refuses_existing_destination(self):
  src=self.source()
  with self.assertRaises(b.Failure):b.clone(src,src)
 def test_rejects_nested_profile_and_app(self):
  with self.assertRaises(b.Failure):b.independent_paths('/tmp/a/app','/tmp/a','/Applications/Arc.app')
 def test_rejects_same_source_and_destination(self):
  with self.assertRaises(b.Failure):b.independent_paths('/Applications/Arc.app','/tmp/data','/Applications/Arc.app')
 def test_detects_source_mutation_during_snapshot(self):
  src=self.source();native=b.clone
  def mutate(s,t):
   native(s,t);(s/'StorableSidebar.json').write_text('{}')
  with patch.object(b,'clone',side_effect=mutate),self.assertRaises(b.Failure):b.prepare_profile(self.root/'copy',src)
 def test_rejects_corrupt_database(self):
  src=self.source();(src/'User Data/Default/Cookies').write_bytes(b'not a database')
  with self.assertRaises(sqlite3.DatabaseError):b.inventory(src)
 def test_identity_is_unique_and_namespaced(self):
  a,c=b.new_identity(),b.new_identity()
  self.assertNotEqual(a,c);self.assertTrue(a['keychainNamespace'].startswith('ArcBorderless/'))
 def test_launcher_keeps_readable_passwords_when_one_entry_cannot_decrypt(self):
  source=(Path(__file__).resolve().parents[1]/'src/Launcher.m').read_text()
  self.assertIn('--enable-features=SkipUndecryptablePasswords',source)
  self.assertIn('--disable-features=ClearUndecryptablePasswords,ClearUndecryptablePasswordsInSync',source)
 def test_atomic_manifest(self):
  p=self.root/'manifest';b.atomic_json(p,{'v':1});b.atomic_json(p,{'v':2})
  self.assertEqual(json.loads(p.read_text()),{'v':2});self.assertFalse(p.with_name('manifest.tmp').exists())
 def test_update_rejects_downgrade_before_quitting(self):
  from types import SimpleNamespace
  cfg={'dataRoot':str(self.root/'data'),'sourceInfo':{'build':'20'}}
  with patch.object(b,'config',return_value=cfg),patch.object(b,'preflight',return_value={'build':'19'}),patch.object(b,'quit_app') as quit:
   with self.assertRaises(b.Failure):b.update(SimpleNamespace(app=self.root/'app',source=self.root/'source-app'))
   quit.assert_not_called()

 def update_fixture(self):
  from types import SimpleNamespace
  app=self.root/'App.app';(app/'Contents/Resources').mkdir(parents=True)
  (app/'binary').write_text('old')
  root=self.root/'profile';root.mkdir();(root/'user-data').write_text('current')
  cfg={'dataRoot':str(root),'bundleID':'local.arc-borderless.test','keychainNamespace':'ArcBorderless/test/','sourceInfo':{'build':'20'}}
  (app/'Contents/Resources/Borderless.plist').write_bytes(plistlib.dumps(cfg))
  return SimpleNamespace(app=app,source=self.root/'Official.app'),root,cfg
 def fake_build(self,source,target,root,identity):
  target.mkdir();(target/'binary').write_text('new')
  return dict(identity,dataRoot=str(root),sourceInfo={'build':'21'})
 def test_failed_update_leaves_app_and_profile_intact(self):
  args,root,cfg=self.update_fixture()
  with patch.object(b,'preflight',return_value={'build':'21'}),patch.object(b,'build_app',side_effect=self.fake_build),patch.object(b,'quit_app'),patch.object(b,'assert_closed'),patch.object(b,'validate',side_effect=b.Failure('startup failed')):
   with self.assertRaises(b.Failure):b.update(args)
  self.assertEqual((args.app/'binary').read_text(),'old')
  self.assertEqual((root/'user-data').read_text(),'current')
 def test_successful_update_retains_profile_and_backs_up_pair(self):
  args,root,cfg=self.update_fixture()
  with patch.object(b,'preflight',return_value={'build':'21'}),patch.object(b,'build_app',side_effect=self.fake_build),patch.object(b,'quit_app'),patch.object(b,'assert_closed'),patch.object(b,'validate',return_value={'hooksInstalled':True}):b.update(args)
  self.assertEqual((args.app/'binary').read_text(),'new')
  self.assertEqual((root/'user-data').read_text(),'current')
  backup=Path(json.loads((root/'installation.json').read_text())['backup'])
  self.assertEqual((backup/'Arc Borderless.app/binary').read_text(),'old')
  self.assertEqual((backup/'profile/user-data').read_text(),'current')
 def test_rejects_symlink_into_original_profile(self):
  src=self.source();(src/'User Data/Default/shared').symlink_to(src/'StorableSidebar.json')
  with self.assertRaises(b.Failure):b.prepare_profile(self.root/'copy',src)

 def rollback_fixture(self):
  from types import SimpleNamespace
  args,root,cfg=self.update_fixture()
  backup=self.root/'backups/snapshot';backup.mkdir(parents=True)
  b.clone(args.app,backup/'Arc Borderless.app');b.clone(root,backup/'profile')
  (backup/'backup.json').write_text(json.dumps({'app':str(args.app),'root':str(root),'build':'20'}))
  (args.app/'binary').write_text('newer');(root/'user-data').write_text('newer data')
  return SimpleNamespace(backup=backup),args.app,root
 def test_rollback_restores_matched_pair_and_preserves_newer_data(self):
  args,app,root=self.rollback_fixture()
  with patch.object(b,'quit_app'),patch.object(b,'assert_closed'):b.rollback(args)
  self.assertEqual((app/'binary').read_text(),'old')
  self.assertEqual((root/'user-data').read_text(),'current')
  saved=next(args.backup.parent.glob('Before-rollback-*'))
  self.assertEqual((saved/'profile/user-data').read_text(),'newer data')
  self.assertEqual((saved/'Arc Borderless.app/binary').read_text(),'newer')
 def test_rollback_profile_copy_failure_restores_current_app(self):
  args,app,root=self.rollback_fixture();native=b.clone
  def fail(src,dst):
   if Path(src).resolve()==(args.backup/'profile').resolve():raise OSError('disk full')
   native(src,dst)
  with patch.object(b,'quit_app'),patch.object(b,'assert_closed'),patch.object(b,'clone',side_effect=fail):
   with self.assertRaises(OSError):b.rollback(args)
  self.assertEqual((app/'binary').read_text(),'newer')
  self.assertEqual((root/'user-data').read_text(),'newer data')
 def test_uninstall_retains_profile_and_moves_only_clone_app(self):
  args,root,cfg=self.update_fixture();home=self.root/'home';home.mkdir()
  with patch.object(b,'quit_app'),patch.object(b,'assert_closed'),patch.object(b.Path,'home',return_value=home):b.uninstall(args)
  self.assertFalse(args.app.exists());self.assertEqual((root/'user-data').read_text(),'current')
  self.assertEqual(len(list((home/'.Trash').glob('*.app'))),1)

if __name__=='__main__':unittest.main()
