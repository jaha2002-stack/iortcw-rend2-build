#!/usr/bin/env python3
"""Read-only provenance gate for exact accepted GitHub Actions run #41019985033."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

BASE_RUN = 41019985033
BASE_COMMIT = 'c653433e1b0a29b2f43f29a240b96a8192acb617'
ARTIFACT_SHA256 = '6385f719eb29bfa2c4edd172cadc9b95b6c5f3d107d7e0e088ed25769a8df57f'
RELEASE_SHA256 = 'e61a38fec90fbdece43364232c0064e40825eb86db7c035df9a46cddcf2cc869'
RENDERER_SHA256 = 'd7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45'
RELEASE_NAME = 'DarkWolf_Volumetric_Sun_HDR16F_Precision_V1_Clean_Production_Win64'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('artifact_zip',type=Path)
    args=p.parse_args(argv)
    path=args.artifact_zip
    try:
        if not path.is_file():
            raise ValueError('base artifact ZIP absent')
        digest=hashlib.sha256()
        with path.open('rb') as inp:
            for chunk in iter(lambda:inp.read(1024*1024),b''):
                digest.update(chunk)
        if digest.hexdigest()!=ARTIFACT_SHA256:
            raise ValueError('WRONG artifact SHA256: '+digest.hexdigest())
        with zipfile.ZipFile(path) as outer:
            if outer.testzip() is not None:
                raise ValueError('outer ZIP CRC failure')
            package_name='dist/'+RELEASE_NAME+'.zip'
            data=outer.read(package_name)
            if sha(data)!=RELEASE_SHA256:
                raise ValueError('WRONG release SHA256')
            audit=json.loads(outer.read('dist/DW_SUN_HDR16F_CLEAN_PRODUCTION_AUDIT.json'))
            if audit.get('release_status')!='CLEAN_PRODUCTION_USER_ACCEPTED' or audit.get('total_files')!=57:
                raise ValueError('clean production acceptance manifest mismatch')
            with zipfile.ZipFile(io.BytesIO(data)) as release:
                if release.testzip() is not None or len(release.namelist())!=57:
                    raise ValueError('release files missing/corrupt')
                dll=release.read(RELEASE_NAME+'/renderer_sp_rend2_x64.dll')
                if sha(dll)!=RENDERER_SHA256:
                    raise ValueError('renderer SHA256 mismatch')
                relmanifest=json.loads(release.read(RELEASE_NAME+'/docs/DW_SUN_HDR16F_V1_RELEASE_MANIFEST.json'))
                if relmanifest['release_renderer_sha256']!=RENDERER_SHA256:
                    raise ValueError('release manifest renderer mismatch')
                for tier in ('PERFORMANCE','BALANCED','QUALITY','HIGH','ULTRA'):
                    cfg=release.read(RELEASE_NAME+'/Main/DW_HDR16F_V1_'+tier+'.cfg').decode('utf8')
                    for effect in ('r_volumetricSun','r_volumetricLocal','r_volumetricFire',
                                   'r_bloom','r_ssgi','r_dwCas','r_dwLut','r_dwA2C'):
                        if 'seta '+effect+' "1"' not in cfg:
                            raise ValueError('effect disabled '+tier+'/'+effect)
        print(json.dumps({'status':'EXACT_41019985033_BASE_VERIFIED','run':BASE_RUN,
                          'commit':BASE_COMMIT,'artifact_sha256':ARTIFACT_SHA256,
                          'release_sha256':RELEASE_SHA256,
                          'renderer_sha256':RENDERER_SHA256,
                          'release_file_count':57,
                          'runtime_modified':False,'effects_preserved':True},indent=2))
        return 0
    except (ValueError,KeyError,zipfile.BadZipFile,OSError) as exc:
        p.exit(2,'HYBRID_RELIGHT_V2_WRONG_BASE: %s\n'%exc)


if __name__=='__main__':
    sys.exit(main())
