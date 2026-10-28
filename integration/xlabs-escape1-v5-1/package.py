#!/usr/bin/env python3
"""Repackage EXACT frozen base using the already-guarded V5 matrix with a
clearly labeled V5.1 repair. No logic, CFG or original production changes."""
import importlib.util,sys
from pathlib import Path
module_path=Path("integration/xlabs-escape1-v5/package.py")
spec=importlib.util.spec_from_file_location("dw_v5_exact_package",module_path)
pkg=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)
assert pkg.NEW_ROOT=="DarkWolf_Xlabs_Tesla_CubeFace_Filter_Escape1_Native_Attribution_Test_V5_Win64"
pkg.NEW_ROOT="DarkWolf_Xlabs_Tesla_CubeFace_Filter_Escape1_Native_Attribution_Test_V5_1_Win64"
pkg.main()
