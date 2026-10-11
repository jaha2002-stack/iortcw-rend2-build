#!/usr/bin/env python3
"""No new semantic failures gate; inherited failures remain explicit FAIL results."""
from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageChops,ImageStat
root=Path(sys.argv[1]);a=root/'baseline-source-regression';b=root/'source-regression'
base=json.loads((a/'ring/analysis.json').read_text());candidate=json.loads((b/'ring/analysis.json').read_text())
new=sorted(set(candidate['failures'])-set(base['failures']))
for label in ['baseline-source','source']:
 p=root/(label+'-regression')
 if (p/'table-analyzer-exit-code.txt').read_text().strip()!='0':new.append(label+': table analyzer failed')
rows=[]
for pa in sorted(a.rglob('*.png')):
 rel=pa.relative_to(a);pb=b/rel
 if not pb.is_file():new.append('missing candidate image '+str(rel));continue
 ia=Image.open(pa).convert('RGB');ib=Image.open(pb).convert('RGB')
 if ia.size!=ib.size:new.append('image size mismatch '+str(rel));continue
 delta=ImageChops.difference(ia,ib);stat=ImageStat.Stat(delta)
 rows.append({'image':str(rel),'mean_abs_rgb_0_255':sum(stat.mean)/3,'baseline_sha256':hashlib.sha256(pa.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(pb.read_bytes()).hexdigest()})
result={'gate':'PASS_NO_NEW_ANALYZER_FAILURES' if not new else 'FAIL','baseline_analyzer_status':base['status'],'candidate_analyzer_status':candidate['status'],'baseline_failures':base['failures'],'candidate_failures':candidate['failures'],'new_failures':new,'images':rows,'scope':'Real Mesa renders. Animation, wall-clock timing and exposure are not synchronized; image errors are descriptive, NOT proof of pixel equivalence or Windows visual acceptance.'}
(root/'regression-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='images'},indent=2))
if new:raise SystemExit(1)
