"""Integration tests against the running app, using the actual trained model.

Run: python -m unittest discover -s tests -v
Set SPORTSVISION_TEST_URL to test a server on a different port.
"""
import io
import json
import os
import unittest
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('SPORTSVISION_TEST_URL', 'http://127.0.0.1:8001')


def post(path, files, field='files'):
    boundary = uuid.uuid4().hex
    chunks = []
    for name, content, mime in files:
        chunks.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode(),
            content, b'\r\n',
        ])
    chunks.append(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(BASE + path, b''.join(chunks),
                                     {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def photo(sport):
    return sport + '.jpg', (ROOT / 'report_assets' / (sport + '.jpg')).read_bytes(), 'image/jpeg'


class OrganizationTests(unittest.TestCase):
    def test_single_and_batch_agree_and_group_correctly(self):
        inputs = [photo(sport) for sport in ('basketball', 'football', 'tennis')]
        code, body, _ = post('/api/organize', inputs)
        self.assertEqual(code, 200)
        batch = json.loads(body)
        self.assertEqual(batch['counts'], {'basketball': 1, 'football': 1, 'tennis': 1})
        self.assertEqual(batch['failed'], 0)
        for index, uploaded in enumerate(inputs):
            code, body, _ = post('/api/predict', [uploaded], field='file')
            self.assertEqual(code, 200)
            single = json.loads(body)
            result = batch['results'][index]
            self.assertEqual(result['index'], index)
            self.assertEqual(result['predicted_sport'], single['predicted_sport'])
            self.assertAlmostEqual(result['confidence'], single['confidence'], places=5)
            self.assertAlmostEqual(sum(item['probability'] for item in single['probabilities']), 1, places=5)

    def test_partial_failures_and_original_bytes_in_zip(self):
        original = photo('football')[1]
        files = [('../../same.jpg', original, 'image/jpeg'), ('same.jpg', original, 'image/jpeg'),
                 ('corrupt.png', b'not an image', 'image/png'), ('empty.jpg', b'', 'image/jpeg'),
                 ('wrong.svg', b'<svg/>', 'image/svg+xml')]
        code, body, _ = post('/api/organize', files)
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertEqual((result['succeeded'], result['failed']), (2, 3))
        self.assertTrue(all(item['error'] for item in result['results'][2:]))
        code, content, headers = post('/api/organize/zip', files)
        self.assertEqual(code, 200)
        self.assertEqual(headers['X-Failed-Count'], '3')
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(set(name for name in archive.namelist() if name.endswith('/')),
                             {'basketball/', 'football/', 'tennis/'})
            paths = [item['archive_path'] for item in result['results'][:2]]
            self.assertNotEqual(paths[0], paths[1])
            for path in paths:
                self.assertNotIn('..', path)
                self.assertEqual(archive.read(path), original)
            self.assertEqual(len(archive.namelist()), 5)

    def test_png_webp_and_all_category_zip(self):
        inputs = [photo('basketball')]
        for sport, fmt in [('football', 'PNG'), ('tennis', 'WEBP')]:
            stream = io.BytesIO()
            with Image.open(io.BytesIO(photo(sport)[1])) as image:
                image.thumbnail((1600, 1600))
                image.save(stream, format=fmt, lossless=True)
            inputs.append((sport + '.' + fmt.lower(), stream.getvalue(), 'image/' + fmt.lower()))
        code, body, _ = post('/api/organize', inputs)
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data['succeeded'], 3, data)
        code, body, _ = post('/api/organize/zip', inputs)
        self.assertEqual(code, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            for index, result in enumerate(data['results']):
                self.assertEqual(archive.read(result['archive_path']), inputs[index][1])

    def test_limits_and_all_invalid_batch(self):
        tiny = ('bad.png', b'bad', 'image/png')
        self.assertEqual(post('/api/organize', [tiny] * 21)[0], 400)
        self.assertEqual(post('/api/organize', [tiny], field='wrong')[0], 400)
        self.assertEqual(post('/api/organize', [tiny])[0], 200)
        self.assertEqual(post('/api/organize/zip', [tiny])[0], 422)
        self.assertEqual(post('/api/organize', [])[0], 400)
        oversized = ('large.png', b'x' * (10 * 1024 * 1024 + 1), 'image/png')
        code, body, _ = post('/api/organize', [oversized, photo('basketball')])
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['failed'], 1)
        # 50 MiB of files plus 1 byte: below envelope cap, above content cap.
        files = [('large.png', b'x' * (10 * 1024 * 1024), 'image/png')] * 5 + [tiny]
        self.assertEqual(post('/api/organize', files)[0], 413)
        self.assertEqual(post('/api/organize', [oversized] * 6)[0], 413)

    def test_dimensions_animation_and_single_error_regression(self):
        large = io.BytesIO()
        Image.new('L', (5001, 5000)).save(large, format='PNG')
        animated = io.BytesIO()
        first = Image.new('RGB', (10, 10), 'red')
        first.save(animated, format='PNG', save_all=True,
                   append_images=[Image.new('RGB', (10, 10), 'blue')], duration=100)
        code, body, _ = post('/api/organize', [('dimensions.png', large.getvalue(), 'image/png'),
                                              ('animated.png', animated.getvalue(), 'image/png'), photo('tennis')])
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['failed'], 2)
        self.assertEqual(json.loads(body)['succeeded'], 1)
        self.assertEqual(post('/api/predict', [('bad.jpg', b'broken', 'image/jpeg')], field='file')[0], 400)
        self.assertEqual(post('/api/predict', [('empty.jpg', b'', 'image/jpeg')], field='file')[0], 400)


if __name__ == '__main__':
    unittest.main()
