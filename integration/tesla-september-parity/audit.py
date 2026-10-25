#!/usr/bin/env python3
"""Audit Tesla parity between proven Sep18 Clean Production and Oct24 feature donor.
Retail game pak and personal settings are never included.
"""
from pathlib import Path
import argparse,difflib,re,json,hashlib,zipfile
p=argparse.ArgumentParser()
p.add_argument("september",type=Path)
p.add_argument("october",type=Path)
p.add_argument("out",type=Path)
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
terms=re.compile(r"tesla|electric|lightning|loper|shadowSource|dlightFxShadow|DWSHADOW_SOURCE|ET_TESLA_EF|WP_TESLA|effect3Time|Dlight.*Shadow",re.I)
roots=(a.september,a.october)
selected=[]
for sp in sorted((roots[0]/"SP/code").rglob("*")):
 if not sp.is_file() or sp.suffix not in (".c",".h",".glsl"):continue
 rel=sp.relative_to(roots[0])
 op=roots[1]/rel
 if not op.exists() or not op.is_file():continue
 old=sp.read_text(errors="replace")
 new=op.read_text(errors="replace")
 if terms.search(old) or terms.search(new):
  selected.append((rel,old,new,sha(sp.read_bytes()),sha(op.read_bytes())))
changed=[(rel,old,new,s1,s2) for rel,old,new,s1,s2 in selected if s1!=s2]
summary=[]
full=[]
for rel,old,new,s1,s2 in changed:
 nd=list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile="sep/"+str(rel),tofile="oct/"+str(rel),n=12))
 relevant=[]
 current=[]
 for line in nd:
  if line.startswith("@@"):
   if current:relevant.append(current)
   current=[line]
  elif current: current.append(line)
 if current:relevant.append(current)
 matches=[h for h in relevant if any(terms.search(v) for v in h if v.startswith(("+","-")) and not v.startswith(("+++","---")))]
 summary.append({"path":str(rel),"sep_sha":s1,"oct_sha":s2,"lines_september":len(old.splitlines()),
   "lines_october":len(new.splitlines()),"total_diff_hunks":len(relevant),"tesla_related_changed_hunks":len(matches),
   "tesla_changed_hunk_headers":[h[0] for h in matches]})
 full.append("# "+str(rel)+"\n"+"\n".join("\n".join(h) for h in matches)+"\n")
base={"baseline":"Sep18 Clean Production actual SHA-locked sources",
      "donor":"Oct24 FourWeek Master V03 after exact 15-file Fire/Tesla revert",
      "tesla_files_seen":len(selected),"tesla_files_changed":len(changed),
      "tesla_relevant_files":[r["path"] for r in summary if r["tesla_related_changed_hunks"]>0],
      "files":summary,"known_risks":[
       "The Sep18 release itself includes Tesla shadow-source classification and cinematic pulses.",
       "A wholesale delete of September Tesla code would NOT reproduce the user-accepted September behavior.",
       "Restore the exact Sep18 stationary Tesla function and any late-added effects for map ET_TESLA_EF.",
       "All shaders, light maps, dynamic-light shadow selection and cgame registration require cross-checks.",
       "Source/PE compile and real gameplay pixel proof are separate acceptance stages."]}
(a.out/"AUDIT_SUMMARY.json").write_text(json.dumps(base,indent=2)+"\n")
(a.out/"TESLA_CHANGED_HUNKS.txt").write_text("\n".join(full))
(a.out/"AUDIT_RU.md").write_text(
 "# Аудит стационарной Tesla: сентябрь против октября\n\n"
 "Сентябрь: исходник в точности воссоздан из Clean Production v1 18.09.2026.\n"
 "Октябрь: FourWeek Master V03; известный Fire/Tesla containment уже удален по полному оригинальному патчу.\n"
 "Таким образом, остающиеся различия по Tesla не относятся к отмененному containment.\n"
 "Сентябрьская Tesla уже была улучшена относительно vanilla RTCW; ее алгоритм следует сохранить, а не удалить.\n\n"
 f"Рассмотрено файлов с Tesla/электрикой: {len(selected)}; изменилось: {len(changed)}.\n\n"+
 "\n".join(f"- \`{r['path']}\`: {r['tesla_related_changed_hunks']} Tesla-ханков из {r['total_diff_hunks']} ({r['sep_sha'][:12]} → {r['oct_sha'][:12]})" for r in summary)+"\n")
with zipfile.ZipFile(a.out/"TESLA_SEPTEMBER_OCTOBER_SOURCE_REVIEW.zip","w",zipfile.ZIP_DEFLATED) as z:
 for rel,old,new,s1,s2 in selected:
  # Snapshots are only source text, never copyrighted retail assets.
  z.writestr("september/"+str(rel),old)
  z.writestr("october_no_containment/"+str(rel),new)
print("TESLA_HISTORICAL_SOURCE_AUDIT_PASS",len(selected),len(changed),base["tesla_relevant_files"],flush=True)
