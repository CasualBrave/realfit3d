import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from apps.api.server import create_app
from realfit3d.adapters.preview import PreviewRuntime, RuntimeUnavailable


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = Mock()
        self.process = Mock()
        self.process.poll.return_value = None
        self.runtime.launch.return_value = self.process
        self.app = create_app({"output_root": str(self.root)}, self.runtime)
        self.app.testing = True
        self.client = self.app.test_client()
        self.state = self.app.extensions["realfit3d"]

    def fit(self):
        return self.client.post('/fit_body', data=dict(height='1.70', weight='58', gender='female'))

    def generate(self, **changes):
        data = dict(upper='00170_upper', lower='00170_lower', motion='0')
        data.update(changes)
        return self.client.post('/generate', data=data)

    def test_page_and_assets(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'/static/app.js', page.data)
        for path in ['/static/app.js', '/static/app.css', '/garment_thumbnail/00170_upper']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()
        self.assertEqual(self.client.get('/garment_thumbnail/unknown').status_code, 404)

    def test_measurements_and_missing_body(self):
        for height in ['nan', 'inf', '183', 'bad']:
            self.assertEqual(self.client.post('/fit_body', data=dict(height=height, weight='58')).status_code, 400)
        self.assertEqual(self.generate().status_code, 400)
        self.runtime.fit.assert_not_called()

    def test_missing_runtime(self):
        self.runtime.check.side_effect = RuntimeUnavailable('missing model')
        self.assertEqual(self.fit().status_code, 503)
        self.assertIsNone(self.state['body'])
        self.assertFalse(self.state['lock'].locked())

    def test_fit_failure_keeps_previous_body(self):
        self.fit()
        old = self.state['body']
        self.runtime.fit.side_effect = RuntimeError('failure')
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assertEqual(self.fit().status_code, 500)
        self.assertIs(self.state['body'], old)
        self.assertFalse(self.state['lock'].locked())

    def test_selection_validation(self):
        self.fit()
        for motion in ['-1', '99', 'x', '']:
            self.assertEqual(self.generate(motion=motion).status_code, 400)
        self.assertEqual(self.generate(upper='00170_lower').status_code, 400)
        self.runtime.launch.assert_not_called()

    def test_launch_failure_releases_lock(self):
        self.fit()
        self.runtime.launch.side_effect = OSError('cannot execute')
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assertEqual(self.generate().status_code, 500)
        self.assertFalse(self.state['lock'].locked())
        self.assertFalse(self.state['runs'])

    def test_lock_rejects_concurrent_mutations(self):
        self.state['lock'].acquire()
        try:
            for response in [self.fit(), self.generate(), self.client.post('/discard_body')]:
                self.assertEqual(response.status_code, 409)
        finally:
            self.state['lock'].release()

    def test_process_failure_and_partial_status(self):
        self.fit()
        response = self.generate()
        self.assertEqual(response.status_code, 200)
        run_id = response.json['run_id']
        self.assertEqual(self.fit().status_code, 409)
        info = self.state['runs'][run_id]
        info['dir'].mkdir()
        (info['dir'] / 'status.json').write_text('{')
        self.assertEqual(self.client.get('/status/' + run_id).json['phase'], 'starting')
        self.process.poll.return_value = 1
        response = self.client.get('/status/' + run_id)
        self.assertEqual(response.json['phase'], 'error')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.post('/discard_body').status_code, 200)
        self.assertTrue(info['dir'].exists())

    def test_media_boundary_and_progress(self):
        self.fit()
        run_id = self.generate().json['run_id']
        directory = self.state['runs'][run_id]['dir']
        directory.mkdir()
        (directory / 'status.json').write_text(json.dumps(dict(phase='full_rendering', preview_ready=True)))
        (directory / 'turntable').mkdir()
        (directory / 'turntable/angle_000.png').write_bytes(b'image')
        (directory / 'secret.pkl').write_bytes(b'private')
        (self.root / 'outside.png').write_bytes(b'outside')
        (directory / 'escape.png').symlink_to(self.root / 'outside.png')
        self.assertEqual(self.client.get('/status/' + run_id).json['turntable_frames'], 1)
        for name in ['escape.png', 'secret.pkl', '../outside.png']:
            self.assertEqual(self.client.get(f'/file/{run_id}/{name}').status_code, 403)
        response = self.client.get(f'/file/{run_id}/turntable/angle_000.png')
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_command_preserves_order_and_explicit_paths(self):
        keys = ['ccraft_python', 'gaugar_python', 'contourcraft_root', 'gaugar_root', 'body_model_root', 'checkpoint', 'cmu_root']
        runtime = PreviewRuntime({key: str(self.root / key) for key in keys})
        body = dict(gender='female', height=1.7, weight=58, betas_path=self.root / 'betas.pkl')
        upper = dict(name='upper', source_gender='male')
        lower = dict(name='lower', source_gender='female')
        command = runtime.command(body, upper, lower, 'motion.npz', 'web_1', 'lower+upper', self.root)
        start = command.index('--garment-names')
        self.assertEqual(command[start + 1:start + 3], ['lower', 'upper'])
        self.assertIn('--output-root', command)
        self.assertIn('--precomputed-betas', command)
        self.assertNotIn('/path/to', ' '.join(command))

    def test_unconfigured_runtime_fails_before_launch(self):
        with self.assertRaises(RuntimeUnavailable):
            PreviewRuntime({}).check()

    def test_opacity_validation_and_command(self):
        self.fit()
        for changes in [dict(opacity_scale=s) for s in ('nan', 'inf', '-1', '2', 'x')] + [
                dict(opacity_mode='unknown'), dict(opacity_mode='v3')]:
            self.assertEqual(self.generate(**changes).status_code, 400)
        self.runtime.launch.assert_not_called()
        self.assertEqual(self.generate(opacity_mode='optical_depth', opacity_scale='.4').status_code, 200)
        self.assertEqual(self.runtime.command.call_args.kwargs,
                         dict(opacity_mode='optical_depth', opacity_scale=.4))

    def test_v3_asset_mapping(self):
        runtime = PreviewRuntime(dict(gg_output_root=str(self.root)))
        upper = dict(name='upper', opacity_controller='opacity_controller_v3/controller.pt')
        lower = dict(name='lower', opacity_controller='opacity_controller_v3_valid_cameras/controller.pt')
        with self.assertRaises(RuntimeUnavailable):
            runtime.opacity_options(upper, lower, 'v3', .5)
        for garment in (upper, lower):
            path = self.root / garment['name'] / garment['opacity_controller']
            path.parent.mkdir(parents=True)
            path.touch()
        options = runtime.opacity_options(upper, lower, 'v3', .5)
        self.assertEqual(options[:4], ['--opacity-mode', 'v3', '--opacity-scale', '0.5'])
        self.assertEqual(options[5], f"lower={self.root / 'lower' / lower['opacity_controller']}")
        self.assertEqual(options[7], f"upper={self.root / 'upper' / upper['opacity_controller']}")
        with self.assertRaises(ValueError):
            runtime.opacity_options(dict(name='upper'), lower, 'v3')
        with self.assertRaises(ValueError):
            runtime.opacity_options(dict(name='upper', opacity_controller='../escape.pt'), lower, 'v3')


if __name__ == '__main__':
    unittest.main()
