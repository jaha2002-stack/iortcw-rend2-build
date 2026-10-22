#!/usr/bin/env python3
"""Inject native Android Graphics Lab HUD into generated SDL2 app (Java source)."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/"app/src/main/java/org/darkwolf/rend2/DarkWolfActivity.java"
s=p.read_text()
assert "private void installTouchControls()" in s
assert "installTouchControls();" in s
s=s.replace("installTouchControls();", "installTouchControls();\n        installLabButton();",1)
s=s.replace("    static native boolean nativeIsUiActive();","    static native void nativeQueueLabCommand(String command);\n    static native String nativeLabCvars();\n    static native boolean nativeIsUiActive();",1)
new=r'''
    private android.widget.Button labButton;
    private final java.util.Map<String,String> labSaved =
        new java.util.LinkedHashMap<>();
    private void labSend(String cmd) {
        if (cmd.length() < 450 && !cmd.contains(";") && !cmd.contains("\n")) {
            nativeQueueLabCommand(cmd);
        }
    }
    private void installLabButton() {
        labButton = new android.widget.Button(this);
        labButton.setText("GRAPHICS LAB");
        labButton.setTextSize(11);
        RelativeLayout.LayoutParams lp = new RelativeLayout.LayoutParams(
            170, 68);
        lp.addRule(RelativeLayout.ALIGN_PARENT_TOP);
        lp.addRule(RelativeLayout.ALIGN_PARENT_RIGHT);
        mLayout.addView(labButton, lp);
        labButton.bringToFront();
        labButton.setOnClickListener(v -> labMenu());
    }
    private void labMenu() {
        final String[] items = {
            "MAP: open any map", "CAMERA: free camera (noclip)",
            "ZOOM IN", "ZOOM OUT", "FULL NATIVE RESOLUTION",
            "ALL CVARS: search & inspect", "LIGHT / SUN", "SHADOWS",
            "SSGI / BLOOM", "CAS / LUT / A2C", "TEXTURES",
            "SAVE PROFILE", "LOAD PROFILE", "RESTART RENDERER",
            "GOTO XYZ: camera waypoint", "FOV: custom zoom",
            "CONTROLS / COMMAND HELP",
            "INPUT & COMMAND MONITOR (toggle)"
        };
        new android.app.AlertDialog.Builder(this)
            .setTitle("DarkWolf Rend2 Graphics Lab")
            .setItems(items, (dialog, which) -> {
                switch (which) {
                case 0: labMap(); break;
                case 1: labSend("noclip"); break;
                case 2: labSend("cg_fov 50"); break;
                case 3: labSend("cg_fov 100"); break;
                case 4: labSend("dw_android_renderScale 100"); break;
                case 5: labCatalog(""); break;
                case 6: labSelect(new String[] {"r_forceSun","r_sunShadows",
                    "r_sunlightMode","r_drawSunRays","r_volumetricSun",
                    "r_volumetricLocal","r_volumetricFire","r_dlightmode"});
                    break;
                case 7: labSelect(new String[] {"r_dlightShadowMaxLights",
                    "r_dlightShadowMapSize","r_staticPromote",
                    "r_staticPromoteMaxLights","r_shadowMapSize"});
                    break;
                case 8: labSelect(new String[] {"r_ssgi","r_bloom",
                    "r_bloomMode","r_bloomThreshold","r_bloomStrength",
                    "r_toneMap","r_hdr"}); break;
                case 9: labSelect(new String[] {"r_dwCas","r_dwCasStrength",
                    "r_dwLut","r_dwLutMode","r_dwLutStrength",
                    "r_dwA2C"}); break;
                case 10: labSelect(new String[] {"r_picmip","r_picmip2",
                    "r_textureMode","r_ext_texture_filter_anisotropic",
                    "r_normalMapping","r_specularMapping","r_parallaxMapping",
                    "r_detailtextures","r_lodbias"}); break;
                case 11: labSend("writeconfig graphics_lab.cfg"); break;
                case 12: labSend("exec graphics_lab.cfg"); break;
                case 13: labSend("vid_restart"); break;
                case 14: labGoto(); break;
                case 15: labFov(); break;
                case 16: labHelp(); break;
                case 17: labToggleInputMonitor(); break;
                }
            }).show();
    }
    private void labSelect(String[] names) {
        new android.app.AlertDialog.Builder(this)
            .setTitle("Choose graphics CVar")
            .setItems(names, (d,i) -> labCvar(names[i],
                labSaved.containsKey(names[i]) ? labSaved.get(names[i]) : ""))
            .show();
    }

    private android.widget.TextView labInputMonitor;
    private boolean labInputMonitorVisible;
    private final android.os.Handler labInputHandler =
        new android.os.Handler(android.os.Looper.getMainLooper());
    private final Runnable labInputMonitorTick = new Runnable() {
        @Override public void run() {
            if (!labInputMonitorVisible || labInputMonitor == null) return;
            try {
                labInputMonitor.setText(nativeLabInputStatus());
            } catch (Throwable t) {
                labInputMonitor.setText("JNI status not available: " +
                    t.getClass().getSimpleName());
            }
            labInputHandler.postDelayed(this, 450L);
        }
    };
    private void labToggleInputMonitor() {
        if (labInputMonitor == null) {
            labInputMonitor = new android.widget.TextView(this);
            labInputMonitor.setTextColor(0xFFFFFFFF);
            labInputMonitor.setTextSize(10f);
            labInputMonitor.setBackgroundColor(0xB8000000);
            labInputMonitor.setPadding(10, 7, 10, 7);
            labInputMonitor.setClickable(false);
            labInputMonitor.setFocusable(false);
            labInputMonitor.setMaxLines(9);
            RelativeLayout.LayoutParams lp =
                new RelativeLayout.LayoutParams(
                    RelativeLayout.LayoutParams.WRAP_CONTENT,
                    RelativeLayout.LayoutParams.WRAP_CONTENT);
            lp.addRule(RelativeLayout.ALIGN_PARENT_TOP);
            lp.addRule(RelativeLayout.ALIGN_PARENT_LEFT);
            lp.setMargins(6, 7, 0, 0);
            mLayout.addView(labInputMonitor, lp);
            mLayout.bringChildToFront(labInputMonitor);
        }
        labInputMonitorVisible = !labInputMonitorVisible;
        labInputMonitor.setVisibility(labInputMonitorVisible ?
            android.view.View.VISIBLE : android.view.View.GONE);
        labInputHandler.removeCallbacks(labInputMonitorTick);
        if (labInputMonitorVisible) {
            labInputHandler.post(labInputMonitorTick);
            android.widget.Toast.makeText(this,
                "Hold W/A/S/D and watch fwd/side, PM state and position. " +
                "Enable noclip to stop any scripted camera.",
                android.widget.Toast.LENGTH_LONG).show();
        }
    }

    private void labHelp() {
        new android.app.AlertDialog.Builder(this)
            .setTitle("Controls and Graphics Lab")
            .setMessage(
                "MOVE: hold W/A/S/D buttons at the lower left, or drag within their pad.\n" +
                "LOOK: drag the right-center of the screen to rotate the camera.\n" +
                "NOCLIP: GRAPHICS LAB > CAMERA: free camera. Move with W/A/S/D; " +
                "JUMP goes UP and C goes DOWN when noclip is active.\n\n" +
                "GRAPHICS SETTINGS: choose a group (SSGI / BLOOM, CAS / LUT / A2C, etc.), " +
                "tap a CVar, enter its VALUE, then APPLY.\n" +
                "QUERY: read Current / Default / Pending / Flags without changing a CVar.\n" +
                "ALL CVARS: search by name, choose a result, tap EDIT, then APPLY.\n" +
                "SAVE PROFILE saves graphics_lab.cfg; LOAD PROFILE restores it.\n" +
                "RESTART RENDERER applies settings marked RESTART REQUIRED.\n" +
                "INPUT & COMMAND MONITOR: toggles an overlay showing the " +
                "real engine command, player position, PM_FREEZE/NOCLIP, " +
                "sv_cheats, pause and last dispatched command.\n" +
                "If Assault starts with a scripted camera, turning noclip ON " +
                "will end that cinematic to let you freely explore.\n" +
                "Keep r_dlightMode=2 and r_forceSun=1.")
            .setPositiveButton("OK", null).show();
    }

    private void labMap() {
        android.widget.EditText value = new android.widget.EditText(this);
        value.setSingleLine(true);
        value.setHint("escape1, factory, assault, crypt1, church, boss1...");
        new android.app.AlertDialog.Builder(this)
            .setTitle("Load RTCW map")
            .setView(value)
            .setPositiveButton("LOAD", (d,w) -> {
                String map=value.getText().toString().trim();
                if (map.matches("[A-Za-z0-9_]{1,48}"))
                    labSend("spdevmap "+map);
            }).setNegativeButton("CANCEL",null).show();
    }

    private void labCatalog(String initialFilter) {
        final String[] raw = nativeLabCvars().split("\n");
        final java.util.ArrayList<String[]> records = new java.util.ArrayList<>();
        for (String line : raw) {
            String[] parts = line.split("\t",-1);
            if (parts.length == 5)
                records.add(parts);
        }
        android.widget.EditText search = new android.widget.EditText(this);
        search.setSingleLine(true);
        search.setText(initialFilter);
        search.setHint("Search registered CVar");
        new android.app.AlertDialog.Builder(this)
            .setTitle("Runtime CVar catalog ("+records.size()+")")
            .setView(search)
            .setPositiveButton("SEARCH",(d,w)->{
                String filter = search.getText().toString().toLowerCase(java.util.Locale.ROOT);
                java.util.ArrayList<String> labels = new java.util.ArrayList<>();
                java.util.ArrayList<String[]> found = new java.util.ArrayList<>();
                for(String[] row:records) {
                    if (!row[0].toLowerCase(java.util.Locale.ROOT).contains(filter)) continue;
                    if(found.size() >= 250) break;
                    found.add(row);
                    labels.add(row[0]+" = "+row[1]);
                }
                new android.app.AlertDialog.Builder(this)
                    .setTitle("CVar results ("+found.size()+")")
                    .setItems(labels.toArray(new String[0]),(dd,index)->labInspect(found.get(index)))
                    .setNegativeButton("CLOSE",null).show();
            }).setNegativeButton("CANCEL",null).show();
    }
    private void labInspect(String[] row) {
        final String key=row[0];
        final int flags;
        try { flags=Integer.parseInt(row[3]); } catch (NumberFormatException e) { return; }
        final boolean locked=(flags & (0x0010|0x0040|0x2000))!=0 ||
            key.equalsIgnoreCase("r_dlightmode") || key.equalsIgnoreCase("r_forcesun");
        final boolean latched=(flags & 0x0020)!=0;
        String message="Current: "+row[1]+"\nDefault: "+row[2]+
            "\nPending: "+(row[4].isEmpty()?"none":row[4])+
            "\nFlags: 0x"+Integer.toHexString(flags)+
            (latched?"\nRESTART REQUIRED":"")+
            (locked?"\nREAD-ONLY / PROTECTED":"");
        android.app.AlertDialog.Builder d=new android.app.AlertDialog.Builder(this)
            .setTitle(key).setMessage(message).setNegativeButton("CLOSE",null);
        if(!locked)d.setPositiveButton("EDIT",(dd,w)->labCvar(key,row[1]));
        d.show();
    }


    private void labGoto() {
        android.widget.EditText xyz = new android.widget.EditText(this);
        xyz.setSingleLine(true);
        xyz.setHint("x y z yaw   (e.g. 100 220 64 90)");
        new android.app.AlertDialog.Builder(this).setTitle("Camera position")
          .setMessage("SetViewPos requires a local cheats-enabled map.")
          .setView(xyz).setPositiveButton("GO",(d,w)->{
             String data=xyz.getText().toString().trim();
             if (data.matches("[-+0-9.]+\\s+[-+0-9.]+\\s+[-+0-9.]+\\s+[-+0-9.]+"))
                 labSend("setviewpos "+data);
          }).setNegativeButton("CANCEL",null).show();
    }
    private void labFov() {
        android.widget.EditText field=new android.widget.EditText(this);
        field.setSingleLine(true);
        field.setInputType(android.text.InputType.TYPE_CLASS_NUMBER |
                           android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        field.setText("90");
        new android.app.AlertDialog.Builder(this).setTitle("Camera field of view")
          .setView(field).setPositiveButton("APPLY",(d,w)->{
              try {
                float f=Float.parseFloat(field.getText().toString());
                if(f>=15 && f<=135) labSend("cg_fov "+f);
              } catch(NumberFormatException ignored) { }
          }).setNegativeButton("CANCEL",null).show();
    }


    private void labQueryCvar(String name) {
        // QUERY reads the renderer value and shows it in a native dialog.
        String[] lines = nativeLabCvars().split("\n");
        for (String line : lines) {
            String[] fields = line.split("\t", -1);
            if (fields.length == 5 && fields[0].equalsIgnoreCase(name)) {
                String details = "Current: " + fields[1] +
                    "\nDefault: " + fields[2] +
                    "\nPending: " + (fields[4].isEmpty() ? "none" : fields[4]) +
                    "\nFlags: " + fields[3];
                new android.app.AlertDialog.Builder(this)
                    .setTitle(fields[0]).setMessage(details)
                    .setPositiveButton("OK", null).show();
                return;
            }
        }
        new android.app.AlertDialog.Builder(this)
            .setTitle(name).setMessage("CVar is not registered.")
            .setPositiveButton("OK", null).show();
    }

    private void labCvar(String name, String current) {
        android.widget.LinearLayout stack = new android.widget.LinearLayout(this);
        stack.setPadding(30,20,30,10);
        stack.setOrientation(android.widget.LinearLayout.VERTICAL);
        android.widget.EditText key = new android.widget.EditText(this);
        key.setSingleLine(true);
        key.setHint("CVar name, e.g. r_bloomStrength");
        key.setText(name);
        android.widget.EditText val = new android.widget.EditText(this);
        val.setSingleLine(true);
        val.setHint("New value");
        val.setText(current);
        stack.addView(key);
        stack.addView(val);
        new android.app.AlertDialog.Builder(this)
            .setTitle("Set renderer CVar")
            .setView(stack)
            .setPositiveButton("APPLY", (d,w) -> {
                String k=key.getText().toString().trim();
                String v=val.getText().toString().trim();
                if (k.matches("[A-Za-z][A-Za-z0-9_]{1,63}") &&
                    v.matches("[A-Za-z0-9_.+-]{1,80}")) {
                    labSaved.put(k,v);
                    labSend(k+" "+v);
                }
            }).setNeutralButton("QUERY", (d,w) -> {
                String k=key.getText().toString().trim();
                if (k.matches("[A-Za-z][A-Za-z0-9_]{1,63}")) labQueryCvar(k);
            }).setNegativeButton("CANCEL",null).show();
    }
'''
needle="    private void prepareFilesystem() {"
assert needle in s
s=s.replace(needle,new+"\n"+needle,1)
# Graphics inspection defaults are not the old ultra-low-performance baseline.
s=s.replace('"+set", "dw_android_ultralow", "1",','"+set", "dw_android_ultralow", "0",')
s=s.replace('"+set", "dw_android_renderScale", "50",','"+set", "dw_android_renderScale", "100",')
s=s.replace('"+set", "r_dlightMode", "0",','"+set", "r_dlightMode", "2",')
s=s.replace('"+set", "r_forceSun", "0",','"+set", "r_forceSun", "1",')
p.write_text(s)
print("GRAPHICS_LAB_ANDROID_UI=INSTALLED")
