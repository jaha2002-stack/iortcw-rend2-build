import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("dw_hdrfix",Path(__file__).resolve().parents[1]/"hdrfix.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class HDRPayloadFixTests(unittest.TestCase):
    def test_valid_hdr_original_check_fails_and_fixed_passes(self):
        data=mod.HDR_HEADER+bytes(mod.PIXEL_BYTES)
        got=mod.validate_header_and_payload(data)
        self.assertEqual(got["header_bytes"],49)
        self.assertEqual(got["payload_bytes"],196608)
        self.assertEqual(got["total_bytes"],196657)
        self.assertTrue(got["stock_bug_rejects"])

    def test_premature_end_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_header_and_payload(mod.HDR_HEADER+bytes(100))

    def test_wrong_header_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_header_and_payload(b'wrong'+bytes(mod.PIXEL_BYTES))

    def test_source_patch_once_preserves_other_paths(self):
        src=mod.MARK+"\n"+"hybridActive "*6+"\n"+mod.OLD+"\nvoid KEEP_UNTOUCHED(void) {}"
        out=mod.transform(src)
        self.assertEqual(out,src.replace(mod.OLD,mod.NEW,1))
        with self.assertRaises(ValueError):
            mod.transform(out)

    def test_unknown_renderer_rejected(self):
        with self.assertRaises(ValueError):
            mod.transform(mod.OLD)
