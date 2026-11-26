#!/usr/bin/env python3
"""Temporary SYNTHETIC unit fixtures only; never gameplay acceptance evidence."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import compare_regressions as reg
import validate_source as source


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class SourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.base = {'a.c': 'a', 'protected.c': 'b', 'shader.glsl': 'c'}
        self.candidate = {**self.base, 'shader.glsl': 'd'}
        self.expected = frozenset({'shader.glsl'})

    def test_shader_change_is_not_byte_identical(self):
        result = source.compare_inventories(self.candidate, self.base, self.expected)
        self.assertFalse(result['shaders_byte_identical'])
        self.assertEqual(result['changed_shaders'], ['shader.glsl'])
        self.assertTrue(result['all_other_source_files_byte_identical'])

    def test_deleted_source_is_blocking(self):
        del self.candidate['protected.c']
        with self.assertRaisesRegex(ValueError, 'deleted='):
            source.compare_inventories(self.candidate, self.base, self.expected)

    def test_added_source_is_blocking(self):
        self.candidate['extra.c'] = 'x'
        with self.assertRaisesRegex(ValueError, 'added='):
            source.compare_inventories(self.candidate, self.base, self.expected)

    def test_unapproved_modification_is_blocking(self):
        self.candidate['protected.c'] = 'x'
        with self.assertRaisesRegex(ValueError, 'Unexpected source delta'):
            source.compare_inventories(self.candidate, self.base, self.expected)

    def test_missing_optimization_is_blocking(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected source delta'):
            source.compare_inventories(self.base, self.base, self.expected)

    def test_empty_inventory_is_blocking(self):
        with self.assertRaisesRegex(ValueError, 'Empty source inventory'):
            source.compare_inventories({}, {}, frozenset())

    def test_non_c_assets_are_included(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'SP/code/assets').mkdir(parents=True)
            (root / 'SP/code/assets/data.bin').write_bytes(b'unit fixture')
            self.assertIn('SP/code/assets/data.bin', source.inventory(root))


class CaptureIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-unit-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / 'baseline-source-regression'
        self.b = self.root / 'source-regression'
        for folder, binary_hash in ((self.a, 'a' * 64), (self.b, 'b' * 64)):
            rows = []
            for name, count in reg.SCENARIOS.items():
                shots = folder / name / 'screenshots'
                shots.mkdir(parents=True)
                for i in range(count):
                    image = Image.new('RGB', (2, 2), (i % 256, 30, 80))
                    image.save(shots / f'unit-{i:03d}.tga')
                    image.save(shots / f'unit-{i:03d}.png')
                rows.append({'scenario': name, 'status': 'CAPTURED', 'exit_code': 0,
                             'capture_ready': True, 'expected': count, 'screenshots': count,
                             'resolution': [2, 2], 'hardware': 'SYNTHETIC_UNIT_FIXTURE_NOT_A_GPU',
                             'preset_sha256': 'c' * 64,
                             'binary_sha256': {'renderer_sp_rend2_x86_64.so': binary_hash}})
            write_json(folder / 'scenario-results.json', rows)
            write_json(folder / 'ring/analysis.json', {'status': 'PASS', 'failures': []})
            (folder / 'table-analyzer-exit-code.txt').write_text('0\n')

    def mutate_row(self, folder, action):
        path = folder / 'scenario-results.json'
        rows = reg.read_json(path)
        action(rows)
        write_json(path, rows)

    def test_complete_synthetic_population(self):
        result = reg.compare(self.root)
        self.assertEqual(result['paired_image_count'], 176)
        self.assertEqual(result['gate'], 'PASS_NO_NEW_ANALYZER_FAILURES')
        self.assertEqual(result['VISUAL_ACCEPTANCE'], 'NOT_RUN')

    def test_empty_capture_is_not_a_pass(self):
        shutil.rmtree(self.a / 'ring/screenshots')
        with self.assertRaisesRegex(ValueError, 'PNG/TGA file set'):
            reg.compare(self.root)

    def test_missing_png_is_blocking(self):
        next((self.b / 'ring/screenshots').glob('*.png')).unlink()
        with self.assertRaisesRegex(ValueError, 'PNG/TGA file set'):
            reg.compare(self.root)

    def test_missing_tga_is_blocking(self):
        next((self.b / 'ring/screenshots').glob('*.tga')).unlink()
        with self.assertRaisesRegex(ValueError, 'PNG/TGA file set'):
            reg.compare(self.root)

    def test_extra_capture_is_blocking(self):
        Image.new('RGB', (2, 2)).save(self.b / 'ring/screenshots/extra.png')
        with self.assertRaisesRegex(ValueError, 'PNG/TGA file set'):
            reg.compare(self.root)

    def test_missing_scenario_is_blocking(self):
        self.mutate_row(self.b, lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, 'incomplete scenario records'):
            reg.compare(self.root)

    def test_duplicate_scenario_is_blocking(self):
        self.mutate_row(self.b, lambda rows: rows.__setitem__(1, rows[0].copy()))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            reg.compare(self.root)

    def test_capture_ready_is_required(self):
        self.mutate_row(self.b, lambda rows: rows[0].update(capture_ready=False))
        with self.assertRaisesRegex(ValueError, 'capture-ready'):
            reg.compare(self.root)

    def test_capture_timeout_is_blocking(self):
        self.mutate_row(self.b, lambda rows: rows[0].update(exit_code=124))
        with self.assertRaisesRegex(ValueError, 'did not succeed'):
            reg.compare(self.root)

    def test_mismatched_presets_are_blocking(self):
        self.mutate_row(self.b, lambda rows: rows[0].update(preset_sha256='d' * 64))
        with self.assertRaisesRegex(ValueError, 'preset_sha256 mismatch'):
            reg.compare(self.root)

    def test_identical_renderers_are_blocking(self):
        self.mutate_row(self.b, lambda rows: rows[0].update(binary_sha256={'renderer_sp_rend2_x86_64.so': 'a' * 64}))
        with self.assertRaisesRegex(ValueError, 'renderer identity'):
            reg.compare(self.root)

    def test_png_must_match_tga(self):
        Image.new('RGB', (2, 2), (255, 255, 255)).save(self.b / 'ring/screenshots/unit-000.png')
        with self.assertRaisesRegex(ValueError, 'TGA pixels'):
            reg.compare(self.root)

    def test_inconsistent_analyzer_status_is_blocking(self):
        write_json(self.b / 'ring/analysis.json', {'status': 'PASS', 'failures': ['unit failure']})
        with self.assertRaisesRegex(ValueError, 'inconsistent analyzer status'):
            reg.compare(self.root)

    def test_inherited_failure_is_not_acceptance(self):
        for folder in (self.a, self.b):
            write_json(folder / 'ring/analysis.json', {'status': 'FAIL', 'failures': ['known unit failure']})
        result = reg.compare(self.root)
        self.assertEqual(result['gate'], 'PASS_NO_NEW_ANALYZER_FAILURES')
        self.assertEqual(result['semantic_acceptance'], 'NOT_ACCEPTED')
        self.assertEqual(result['candidate_failures'], ['known unit failure'])

    def test_new_failure_is_blocking(self):
        write_json(self.b / 'ring/analysis.json', {'status': 'FAIL', 'failures': ['new unit failure']})
        self.assertEqual(reg.compare(self.root)['gate'], 'FAIL')

    def test_table_analyzer_failure_is_blocking(self):
        (self.b / 'table-analyzer-exit-code.txt').write_text('1\n')
        with self.assertRaisesRegex(ValueError, 'table analyzer failed'):
            reg.compare(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
