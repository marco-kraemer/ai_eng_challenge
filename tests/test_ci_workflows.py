from pathlib import Path
import unittest
import yaml


class CIWorkflowTests(unittest.TestCase):
    def test_checks_cover_real_commands_without_provider_secrets(self):
        path = Path('.github/workflows/checks.yml')
        data = yaml.safe_load(path.read_text())
        text = path.read_text()
        self.assertIn('pull_request', text)
        self.assertIn('push', text)
        for command in ('unittest discover', 'mypy app', 'node tests/test_frontend.js', 'browser_category_scope.py', 'REDIS_TEST_CONTAINER'):
            self.assertIn(command, text)
        self.assertNotIn('secrets.', text)
        self.assertEqual(data['permissions']['contents'], 'read')

    def test_paid_evaluation_is_manual_only_and_bounded(self):
        text = Path('.github/workflows/live-evaluation.yml').read_text()
        self.assertIn('workflow_dispatch', text)
        self.assertNotIn('pull_request:', text)
        self.assertNotIn('push:', text)
        self.assertIn('--budget-usd', text)
        self.assertIn('upload-artifact', text)
