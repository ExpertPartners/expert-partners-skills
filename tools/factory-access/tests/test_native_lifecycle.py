"""Static instruction contracts, not native runtime or qualification evidence."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
SKILLS = 'plugins/operating-doctrine/skills/'


def source(path):
    baseline = os.environ.get('NATIVE_FACTORY_BASELINE')
    if baseline:
        return subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':' + path], text=True)
    return (ROOT / path).read_text()


class NativeLifecycleContracts(unittest.TestCase):
    def test_wrong_workspace_does_not_require_issue_or_queue(self):
        home = source(SKILLS + 'session-home/SKILL.md')
        route = home.split('**Code work in the wrong workspace.**', 1)[1].split('\n-', 1)[0]
        self.assertIn('No GitHub issue, Hub record or job queue is a prerequisite', route)
        self.assertIn('isolated branch/worktree', route)
        self.assertIn('do not discard user work', route)

    def test_live_placement_and_creation_gate_cannot_be_skipped(self):
        repo = source(SKILLS + 'repo-standards/SKILL.md')
        gate = repo.split('### Stage A, the new-repo gate', 1)[1].split('### Stage B', 1)[0]
        for phrase in ('GitHub Archive Index sheet live', 'enumerate the whole org',
                       'existing repo and folder', 'technical or ownership reason',
                       'duplicate-truth risk', 'cannot reach live org or canon state returns neither verdict'):
            self.assertIn(phrase, gate)
        self.assertIn('Only after `NEW REPO JUSTIFIED` may stage B proceed', gate)

    def test_registration_preserves_archive_receipts_and_requires_readback(self):
        repo = source(SKILLS + 'repo-standards/SKILL.md')
        birth = repo.split('### Stage B', 1)[1].split('## Path two', 1)[0]
        self.assertIn('purpose, entity type, owner, deployment and Factory agent instructions', birth)
        self.assertIn('Preserve historical archive/worktree rows and copied-SHA receipts', birth)
        self.assertIn('Re-read the sheet to verify the landed row', birth)

    def test_auto_is_default_without_byok_or_issue_dependency(self):
        operator = source(SKILLS + 'factory-operator/SKILL.md')
        self.assertIn('Auto Model and available Factory allowance are the default', operator)
        self.assertIn('BYOK is optional, never a prerequisite or blocker', operator)
        self.assertIn('A GitHub issue or Hub record is optional', operator)
        self.assertNotIn('Auto only when', operator)
        self.assertNotIn('Otherwise pin.', operator)

    def test_completion_retains_approvals_and_different_evidence_stages(self):
        doctrine = source(SKILLS + 'operating-doctrine/SKILL.md')
        current = doctrine.split('## The Job Report And Archive Readiness', 1)[1].split('\n---', 1)[0]
        self.assertNotIn('Use job_create or job_claim', current)
        self.assertIn('independent review', current)
        self.assertIn('merge, release, spending, access and production approvals', current)
        self.assertIn('source PR, merge, installed delivery and active runtime use are separate', current)

    def test_retirement_does_not_follow_from_inactivity(self):
        repo = source(SKILLS + 'repo-standards/SKILL.md')
        self.assertIn('Inactivity alone never proves no dependents', repo)
        self.assertIn('Keep stored readiness scores and denominators unchanged', repo)
        self.assertIn('automatic readiness evaluation never silently repairs, renames, archives', repo)

    def test_human_browser_handoff_stays_in_closable_owned_tab(self):
        for path in ('browser-automation/SKILL.md', 'ember-browser-routing/SKILL.md'):
            text = ' '.join(source(SKILLS + path).split())
            self.assertIn('human verification handoff', text, path)
            self.assertIn('verify an authorized route that can close it', text, path)
            self.assertIn('No completed owned tab survives', text, path)

    def test_existing_validator_and_release_producers_remain_available(self):
        for path in ('tools/validate-job.sh', 'tools/release/release.py',
                     'tools/skill-deploy/deploy-skill.sh', '.changeset/README.md'):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == '__main__':
    unittest.main()
