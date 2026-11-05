import importlib.util
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('chrome_quiet', Path(__file__).with_name('chrome_quiet.py'))
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / 'Applications/Chrome AI.app').mkdir(parents=True)
        self.agent = self.home / 'Library/LaunchAgents/com.expertpartners.chrome-quiet.plist'
        self.agent.parent.mkdir(parents=True)
        self.old_agent = plistlib.dumps({'Label': 'old', 'RunAtLoad': True})
        self.agent.write_bytes(self.old_agent)
        self.original = {'persistent-apps': [
            {'tile-data': {'file-label':'Mail', 'file-data':{'_CFURLString':'file:///Applications/Mail.app/'}}},
            {'tile-data': {'file-label':'Google Chrome', 'file-data':{'_CFURLString':'file:///Applications/Google%20Chrome.app/'}, 'book':b'oldbookmark'}}],
            'other-preference': 42}
        self.dock = self.original

    def fake_run(self, *args, **kwargs):
        if args[:3] == ('/usr/bin/defaults', 'import', 'com.apple.dock'):
            self.dock = plistlib.loads(Path(args[3]).read_bytes())

    def test_install_and_rollback_preserve_unrelated_changes(self):
        receipt = self.home / 'backup'
        with patch.object(q, 'export_dock', side_effect=lambda:plistlib.dumps(self.dock)), patch.object(q, 'run', side_effect=self.fake_run):
            q.install(self.home, receipt)
            self.assertEqual(self.dock['persistent-apps'][0], self.original['persistent-apps'][0])
            self.assertNotIn('book', self.dock['persistent-apps'][1]['tile-data'])
            self.assertEqual(plistlib.loads(self.agent.read_bytes())['ProgramArguments'],
                             ['/usr/bin/open', str(self.home / 'Applications/Chrome AI.app')])
            self.dock['other-preference'] = 73
            self.dock['persistent-apps'].append({'tile-data':{'file-label':'Later app'}})
            q.rollback(self.home, receipt)
            self.assertEqual(self.agent.read_bytes(), self.old_agent)
            self.assertEqual(self.dock['persistent-apps'][1], self.original['persistent-apps'][1])
            self.assertEqual(self.dock['other-preference'], 73)
            self.assertEqual(len(self.dock['persistent-apps']), 3)

    def test_missing_chrome_tile_writes_no_config(self):
        self.dock['persistent-apps'] = self.dock['persistent-apps'][:1]
        with patch.object(q, 'export_dock', return_value=plistlib.dumps(self.dock)), patch.object(q, 'run') as run:
            with self.assertRaises(RuntimeError):
                q.install(self.home, self.home / 'backup')
            run.assert_not_called()
        self.assertEqual(self.agent.read_bytes(), self.old_agent)

    def test_concurrent_dock_change_refused(self):
        before = plistlib.dumps(self.original)
        after = plistlib.dumps({'persistent-apps':[], 'other-preference':99})
        with patch.object(q, 'export_dock', side_effect=[before, after]), patch.object(q, 'run') as run:
            with self.assertRaises(RuntimeError):
                q.install(self.home, self.home / 'backup')
            run.assert_not_called()
        self.assertEqual(self.agent.read_bytes(), self.old_agent)

    def test_partial_install_has_rollback_manifest(self):
        receipt = self.home / 'backup'
        with patch.object(q, 'export_dock', return_value=plistlib.dumps(self.dock)), patch.object(q, 'run', side_effect=OSError('write failed')):
            with self.assertRaises(OSError):
                q.install(self.home, receipt)
        self.assertEqual(json.loads((receipt / 'manifest.json').read_text())['agent'], str(self.agent))
        self.assertEqual((receipt / 'launchagent.before.plist').read_bytes(), self.old_agent)

    def test_existing_ai_agent_reused_instead_of_duplicate(self):
        ai = self.agent.with_name('com.expertpartners.chrome-ai.plist')
        self.agent.rename(ai)
        with patch.object(q, 'export_dock', return_value=plistlib.dumps(self.dock)), patch.object(q, 'run', side_effect=self.fake_run):
            q.install(self.home, self.home / 'backup')
        self.assertFalse(self.agent.exists())
        self.assertEqual(plistlib.loads(ai.read_bytes())['Label'], 'old')
        self.assertEqual(json.loads((self.home/'backup/manifest.json').read_text())['agent'],str(ai))

    def test_multiple_agents_refused_before_mutation(self):
        self.agent.with_name('com.expertpartners.chrome-ai.plist').write_bytes(self.old_agent)
        with patch.object(q, 'run') as run:
            with self.assertRaises(RuntimeError):
                q.install(self.home, self.home / 'backup')
            run.assert_not_called()
        self.assertFalse((self.home / 'backup').exists())


if __name__ == '__main__':
    unittest.main()
