#!/usr/bin/env bash
set -Eeuo pipefail

runtime_root="${1:-runtime}"
evidence_root="${2:-evidence}"
probe_log="$evidence_root/probe-qconsole.log"
exe="$(find "$runtime_root" -maxdepth 1 -type f -iname 'iowolfsp*' -print -quit)"
test -n "$exe"

python3 testlab/scripts/make_table_cluster_cfg.py "$probe_log" "$runtime_root/main/testlab_table_baseline.cfg" --label baseline --exclude-shadow-fixture -1
python3 testlab/scripts/make_table_cluster_cfg.py "$probe_log" "$runtime_root/main/testlab_table_exclude742.cfg" --label exclude742 --exclude-shadow-fixture 742
python3 testlab/scripts/make_table_cluster_cfg.py "$probe_log" "$runtime_root/main/testlab_table_exclude744.cfg" --label exclude744 --exclude-shadow-fixture 744

rm -rf "$evidence_root/table-cluster"
mkdir -p "$evidence_root/table-cluster"

for label in baseline exclude742 exclude744; do
  home_dir="home_table_$label"
  rm -rf "$home_dir"
  mkdir -p "$home_dir"
  cfg="testlab_table_$label.cfg"

  set +e
  LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a timeout -k 15s 240s "$exe" \
    +set fs_basepath "$PWD/$runtime_root" +set fs_homepath "$PWD/$home_dir" \
    +set com_introplayed 1 +set logfile 2 +set r_fullscreen 0 +set dw_testAutomation 1 \
    +set r_renderer rend2 +set r_mode -1 +set r_customwidth 800 +set r_customheight 600 \
    +spdevmap escape1 +wait 300 +exec "$cfg"
  rc=$?
  set -e

  out="$evidence_root/table-cluster/$label"
  mkdir -p "$out/screenshots"
  echo "$rc" > "$out/exit-code.txt"
  qlog="$(find "$home_dir" -type f \( -iname 'qconsole.log' -o -iname 'rtcwconsole.log' \) -print -quit)"
  test -n "$qlog"
  cp "$qlog" "$out/qconsole.log"
  find "$home_dir" -type f -path "*/screenshots/testlab_table_${label}_*.tga" -exec cp -a {} "$out/screenshots/" \;

  if [ "$rc" -ne 0 ]; then
    echo "ERROR: historical table pass $label exited with code $rc" >&2
    exit 1
  fi
done

python3 testlab/scripts/analyze_table_ab.py "$evidence_root/table-cluster" "$evidence_root/table-cluster/image-diff-summary.json"
echo "Historical table shadow A/B PASS"
