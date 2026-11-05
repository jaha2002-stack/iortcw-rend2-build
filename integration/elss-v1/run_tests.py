#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'integration/iflc-v15u/run_tests.py',str(src),str(ev/'iflc15u_regression')],check=True)
code=src/'SP/code/rend2'
elss=(code/'tr_elss.inc').read_text();electric=(code/'tr_electric_fixture.inc').read_text();init=(code/'tr_init.c').read_text();scene=(code/'tr_scene.c').read_text()
checks={
 'dedicated_master':'r_dwElectricLightControl' in init and '"0", CVAR_ARCHIVE' in init,
 'commands':all(x in init for x in ('dw_el_select','dw_el_self_pick','dw_el_info','dw_el_set','dw_el_save','dw_el_reload','dw_el_list')),
 'manual_owner_key':'R_ELSS_KeyForLight' in elss and 'staticPromoteFixtureId' in elss and 'native:' in elss,
 'manual_arch_guard':'R_IFLC_SelfSamePlaneAsLargeArchitecture' in elss,
 'real_mesh_contact':'R_IFLC_SelfContact' in elss,
 'bounded_group':'hi[0]-lo[0]>192' in elss and 'hi[2]-lo[2]>256' in elss,
 'profile_bsp_guard':'bsp %08x' in elss and 'electricshadows/%s.elss' in elss,
 'save_backup_verify':'temporary write failed' in elss and 'backup verification failed' in elss,
 'explicit_original_on':'selfShadow==2' in elss and 'if(fixture)*fixture=0' in elss,
 'manual_negative_fixture':'fixture<0' in electric and 'R_ELSS_SuppressManualDrawSurf' in electric,
 'auto_preserved':'R_ElectricFixtureForLightAuto' in electric and 'return R_ElectricFixtureForLightAuto(dl)' in electric,
 'frame_before_capture':'R_ELSS_Frame(fd);' in scene and 'R_ELSS_CaptureShadowSlots(fd);' in scene,
 'no_shadow_budget_change':'r_dlightShadowMaxLights' not in elss,
 'no_direct_mutation':'.color' not in elss and 'iflcBaseRadius' not in elss,
}
assert all(checks.values()),checks
(ev/'ELSS_V1_STATIC_SAFETY.json').write_text(json.dumps(checks,indent=2)+'\n')
print('ELSS_V1_STATIC_SAFETY_PASS',len(checks))
