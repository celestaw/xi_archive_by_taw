import importlib.util
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('deployment_check', SITE / 'scripts/check_deployment.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class HostingTests(unittest.TestCase):
    def test_service_roots_runtimes_and_api_prefix_are_consistent(self):
        config = json.loads((SITE / 'vercel.json').read_text(encoding='utf-8'))
        def destination(path):
            return next(rule['destination']['service'] for rule in config['rewrites'] if re.fullmatch(rule['source'], path))
        api = json.loads((SITE / 'contracts/openapi.json').read_text(encoding='utf-8'))
        for route in api['paths']:
            self.assertEqual(destination(route), 'backend', route)
        for route in ['/', '/songs', '/songs.csv', '/_next/static/client.js', '/works/XI-025']:
            self.assertEqual(destination(route), 'web', route)
        for service in config['services'].values():
            self.assertTrue((SITE / service['root']).is_dir())
        backend = config['services']['backend']
        self.assertEqual(backend['framework'], 'fastapi')
        self.assertTrue((SITE / backend['root'] / (backend['entrypoint'].split(':')[0] + '.py')).is_file())
        web = json.loads((SITE / 'web/package.json').read_text(encoding='utf-8'))
        root = json.loads((SITE / 'package.json').read_text(encoding='utf-8'))
        lock = json.loads((SITE / 'package-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(web['engines'], lock['packages']['web']['engines'])
        self.assertEqual(web['engines'], root['engines'])

    def test_vercel_does_not_keep_the_localhost_next_rewrite(self):
        script = "const {default:c}=await import('./next.config.mjs');process.stdout.write(JSON.stringify(await c.rewrites()))"
        env = {**os.environ, 'VERCEL': '1', 'XI_BACKEND_ORIGIN': 'http://127.0.0.1:8210'}
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=SITE / 'web', env=env, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [])
        del env['VERCEL']
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=SITE / 'web', env=env, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [{'source': '/api/v1/:path*', 'destination': 'http://127.0.0.1:8210/api/v1/:path*'}])

    def test_smoke_check_preserves_csv_punctuation_duplicates_and_html_entities(self):
        titles = ['a,b', '"quoted"', 'a,b', 'x & y']
        payload = '\ufeff曲名\r\n"a,b"\r\n"""quoted"""\r\n"a,b"\r\nx & y\r\n'.encode()
        self.assertEqual(check.check_csv(payload, titles), 4)
        with self.assertRaises(check.CheckFailed):
            check.check_csv(payload, titles[:-1])
        parts = check.PageParts()
        parts.feed('<textarea id="song-titles">x &amp; y</textarea>')
        self.assertEqual(''.join(parts.titles), 'x & y')

    def test_smoke_check_rejects_internal_fields_and_authenticated_origins(self):
        with self.assertRaises(check.CheckFailed):
            check.public_fields({'items': [{'identity_note': 'private'}]})
        for url in ['https://user:password@example.com', 'https://example.com/?token=value', 'https://example.com/songs']:
            with self.assertRaises(check.CheckFailed):
                check.base_url(url)


if __name__ == '__main__':
    unittest.main()
