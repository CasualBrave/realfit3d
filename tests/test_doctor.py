"""Keep implementation status separate from configured asset readiness."""
import unittest

from realfit3d.doctor import inspect


class DoctorTests(unittest.TestCase):
    def test_opacity_status_does_not_claim_asset_or_gpu_readiness(self):
        report = inspect({})
        self.assertEqual(
            report['opacity'],
            'integrated: direct/optical_depth/v3; per-garment controllers and training inputs are not checked',
        )
        self.assertFalse(report['paths_ready'])
        self.assertFalse(report['gpu_parity_verified'])
        self.assertIn('no model is loaded', report['note'])


if __name__ == '__main__':
    unittest.main()
