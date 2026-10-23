import contextlib
import importlib.util
import io
import json
import pathlib
import unittest
import urllib.error

spec = importlib.util.spec_from_file_location('sync', pathlib.Path(__file__).parents[1] / 'scripts/sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class Response(io.BytesIO):
    code = 200

class SyncTests(unittest.TestCase):
    def invoke(self, body, status=200, raw=False):
        calls = []
        def opener(request, timeout):
            calls.append((request, timeout))
            stream = Response(body if raw else json.dumps(body).encode())
            stream.code = status
            if status >= 300:
                raise urllib.error.HTTPError(sync.ENDPOINT, status, 'error', {}, stream)
            return stream
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = sync.main(opener, {'OAI_SITES_AUTHORIZATION': 'do-not-log-token', 'SYNC_API_KEY': 'do-not-log-key'})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 240)
        self.assertEqual(calls[0][0].get_method(), 'POST')
        self.assertNotIn('do-not-log', output.getvalue())
        return code, output.getvalue()

    def test_complete_live_success(self):
        self.assertEqual(self.invoke({'status':'SUCCEEDED','counters':dict(sync.EXPECTED)})[0], 0)

    def test_each_counter_is_required_exactly(self):
        for key, value in sync.EXPECTED.items():
            for invalid in [None, True, str(value), -1]:
                if type(invalid) is type(value) and invalid == value:
                    continue
                with self.subTest(key=key, value=invalid):
                    counters = dict(sync.EXPECTED); counters[key] = invalid
                    self.assertEqual(self.invoke({'status':'SUCCEEDED','counters':counters})[0], 1)

    def test_500_has_safe_diagnostic_and_never_replays(self):
        code, output = self.invoke({'status':'FAILED','runId':'12345678-1234-1234-1234-123456789abc','error':'OTTO-Mengen-Readback weicht bei 7 SKU ab'}, 500)
        self.assertEqual(code, 1)
        self.assertIn('OTTO_QUANTITY_READBACK_MISMATCH', output)
        self.assertIn('12345678-1234-1234-1234-123456789abc', output)

    def test_private_errors_and_injection_are_not_printed(self):
        code, output = self.invoke({'status':'FAILED','error':'private-order secret\n::warning::injected','runId':'private-customer','counters':{'catalog':'private-token','customer':'private-order'}}, 500)
        self.assertEqual(code, 1)
        self.assertNotIn('private-', output)
        self.assertNotIn('::warning::', output)

    def test_invalid_bodies_redirects_and_skips_fail(self):
        for body in [None, [], {}, {'status':'SKIPPED'}, {'status':'SUCCEEDED','counters':None}]:
            self.assertEqual(self.invoke(body)[0], 1)
        self.assertEqual(self.invoke(b'<html>secret</html>', raw=True)[0], 1)
        self.assertEqual(self.invoke(b'x'*65537, raw=True)[0], 1)
        self.assertEqual(self.invoke({}, 302)[0], 1)
        self.assertIsNone(sync.NoRedirect().redirect_request(None,None,302,'',{},'https://example.test'))

    def test_timeout_and_missing_auth_never_retry(self):
        calls = []
        def opener(*args, **kwargs):
            calls.append(1); raise TimeoutError('secret')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.main(opener,{}), 1)
            self.assertEqual(len(calls), 0)
            self.assertEqual(sync.main(opener,{'OAI_SITES_AUTHORIZATION':'a','SYNC_API_KEY':'b'}), 1)
            self.assertEqual(len(calls), 1)

if __name__ == '__main__':
    unittest.main()
