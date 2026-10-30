import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'gold-macro-intelligence'
SOURCES = ['README.md', 'README.zh-CN.md'] + [f'docs/{name}{lang}.md' for name in ('USAGE', 'METHODOLOGY', 'DATA_SOURCES', 'LIMITATIONS', 'STATUS') for lang in ('', '.zh-CN')]
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
PUBLIC = 'https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/'


def reference_text(name):
    source = ROOT / name
    def replace(match):
        target = match.group(1)
        path = urlsplit(target).path
        if not path or urlsplit(target).scheme or path.startswith('#'):
            return match.group(0)
        resolved = (source.parent / unquote(path)).resolve()
        relative = resolved.relative_to(ROOT).as_posix()
        if relative in SOURCES:
            return match.group(0)
        return match.group(0).replace(target, PUBLIC + relative + (('#' + urlsplit(target).fragment) if urlsplit(target).fragment else ''))
    return LINK.sub(replace, source.read_text(encoding='utf-8'))


class SkillPortabilityTests(unittest.TestCase):
    def test_reference_copies_are_in_sync(self):
        for name in SOURCES:
            with self.subTest(name=name):
                self.assertEqual((SKILL / 'references' / name).read_text(encoding='utf-8'), reference_text(name))

    def test_isolated_skill_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'skill'
            shutil.copytree(SKILL, dest, symlinks=False)
            for document in dest.rglob('*.md'):
                content = document.read_text(encoding='utf-8')
                self.assertTrue(content.strip())
                for target in LINK.findall(content):
                    parsed = urlsplit(target)
                    if parsed.scheme or not parsed.path:
                        continue
                    with self.subTest(document=document, target=target):
                        path = (document.parent / unquote(parsed.path)).resolve()
                        self.assertTrue(path.is_relative_to(dest.resolve()), target)
                        self.assertTrue(path.is_file(), target)
                        self.assertTrue(path.read_text(encoding='utf-8').strip())


class AnalyzeInputTests(unittest.TestCase):
    def invoke(self, path):
        return subprocess.run([sys.executable, '-m', 'gmi', 'analyze', str(path)], cwd=ROOT, text=True, capture_output=True)

    def test_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [('missing.json', '{}', "missing required field 'as_of'"), ('array.json', '[]', 'expected an analysis JSON object'), ('broken.json', '{ broken', 'Expecting property name')]
            for name, content, message in cases:
                path = root / name
                path.write_text(content)
                result = self.invoke(path)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
            result = self.invoke(root / 'absent.json')
            self.assertEqual(result.returncode, 2)
            self.assertIn('No such file', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_valid_analysis_matches_baseline(self):
        result = self.invoke(ROOT / 'examples/analysis.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads((ROOT / 'examples/analysis.expected.json').read_text()))

class VersionConsistencyTests(unittest.TestCase):
    def test_release_version_metadata_and_cli(self):
        import gmi
        expected = '1.0.1'
        project = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        fixture = json.loads((ROOT / 'fixtures/gmi_portability_expected.json').read_text(encoding='utf-8'))
        self.assertEqual(gmi.__version__, expected)
        self.assertRegex(project, r'(?m)^version = "' + re.escape(expected) + r'"$')
        self.assertRegex(skill, r'(?m)^  version: "' + re.escape(expected) + r'"$')
        self.assertEqual(fixture['gmi_version'], expected)
        result = subprocess.run([sys.executable, '-m', 'gmi', 'env-check'], cwd=ROOT, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['gmi_version'], expected)
