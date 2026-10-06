#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SDL="$WORKDIR/SDL2"
RUNTIME="$WORKDIR/native-runtime"
MODULES="$WORKDIR/game-modules"
OUT="$WORKDIR/android-apk"
PROJECT="$OUT/project"
DIST="$OUT/dist"
NDK="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
TOOL="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
APK_NAME="DarkWolf-ioRTCW-Rend2-Android-v0.1-ARM64-Debug.apk"

test -s "$RUNTIME/bin/libmain.so"
test -s "$RUNTIME/bin/libSDL2.so"
test -s "$MODULES/bin/cgame.sp.arm64.so"
test -s "$MODULES/bin/qagame.sp.arm64.so"
test -s "$MODULES/bin/ui.sp.arm64.so"
test -d "$SDL/android-project"

# Do not use grep -q here under pipefail: llvm-nm can see SIGPIPE and return 74.
"$TOOL/llvm-nm" -D --defined-only "$RUNTIME/bin/libmain.so" > "$WORKDIR/a4-libmain-symbols.txt"
grep -E '[[:space:]]SDL_main$' "$WORKDIR/a4-libmain-symbols.txt" >/dev/null
echo "A4_SDL_MAIN_EXPORT=PASS"

rm -rf "$OUT"
mkdir -p "$PROJECT/app/src/main/java" "$PROJECT/app/src/main/res" \
  "$PROJECT/app/src/main/jniLibs/arm64-v8a" \
  "$PROJECT/app/src/main/assets/darkwolf-runtime/main" "$DIST"

cp -a "$SDL/android-project/app/src/main/java/org" "$PROJECT/app/src/main/java/"
cp -a "$SDL/android-project/app/src/main/res/." "$PROJECT/app/src/main/res/"
mkdir -p "$PROJECT/app/src/main/java/org/darkwolf/rend2"
cp -a "$SDL/android-project/gradle" "$PROJECT/"
cp "$SDL/android-project/gradlew" "$PROJECT/"
chmod +x "$PROJECT/gradlew"

cat > "$PROJECT/settings.gradle" <<'EOF'
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "DarkWolfRend2Android"
include(":app")
EOF

cat > "$PROJECT/build.gradle" <<'EOF'
plugins {
    id 'com.android.application' version '8.6.0' apply false
}
EOF

cat > "$PROJECT/gradle.properties" <<'EOF'
org.gradle.jvmargs=-Xmx3g -Dfile.encoding=UTF-8
android.useAndroidX=false
android.nonTransitiveRClass=true
EOF

cat > "$PROJECT/app/build.gradle" <<'EOF'
plugins {
    id 'com.android.application'
}

android {
    namespace 'org.darkwolf.rend2'
    compileSdk 35

    defaultConfig {
        applicationId 'org.darkwolf.rend2'
        minSdk 29
        targetSdk 35
        versionCode 1
        versionName '0.1-a4'
        ndk {
            abiFilters 'arm64-v8a'
        }
    }

    buildTypes {
        debug {
            debuggable true
            jniDebuggable true
            minifyEnabled false
        }
    }

    sourceSets {
        main {
            jniLibs.srcDirs = ['src/main/jniLibs']
            assets.srcDirs = ['src/main/assets']
        }
    }

    packagingOptions {
        jniLibs {
            useLegacyPackaging = true
        }
    }

    lint {
        abortOnError false
    }
}
EOF

cat > "$PROJECT/app/src/main/java/org/darkwolf/rend2/LauncherActivity.java" <<'EOF'
package org.darkwolf.rend2;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentResolver;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public final class LauncherActivity extends Activity {
    private static final int PICK_RTCW_FOLDER = 4242;
    private static final String[] REQUIRED = {
            "pak0.pk3",
            "sp_pak1.pk3",
            "sp_pak2.pk3",
            "sp_pak3.pk3",
            "sp_pak4.pk3",
            "sp_rend2_shaders0.pk3"
    };

    private File retailMain;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        File external = getExternalFilesDir(null);
        File root = external != null
                ? new File(external, "DarkWolfRTCW")
                : new File(getFilesDir(), "DarkWolfRTCW");
        retailMain = new File(root, "main");
        if (!retailMain.mkdirs() && !retailMain.isDirectory()) {
            showFatal("Cannot create game data directory:\n" + retailMain);
            return;
        }

        if (hasRequiredData()) {
            showReady();
            return;
        }

        showImporter();
    }

    private void showImporter() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        box.setPadding(pad, pad, pad, pad);

        TextView text = new TextView(this);
        text.setText(
                "DarkWolf RTCW Rend2\n\n" +
                "Game data is required before first launch.\n" +
                "Tap the button and select the folder containing:\n\n" +
                "pak0.pk3\nsp_pak1.pk3\nsp_pak2.pk3\nsp_pak3.pk3\n" +
                "sp_pak4.pk3\nsp_rend2_shaders0.pk3\n\n" +
                "The files will be copied into the app's private game directory."
        );
        text.setTextSize(18f);

        Button button = new Button(this);
        button.setText("SELECT RTCW PK3 FOLDER");
        button.setOnClickListener(v -> openFolderPicker());

        Button logButton = new Button(this);
        logButton.setText("SHOW LAST STARTUP LOG");
        logButton.setOnClickListener(v -> showLastLog());

        box.addView(text);
        box.addView(button);
        box.addView(logButton);
        setContentView(box);
    }

    private void openFolderPicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION |
                Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent, PICK_RTCW_FOLDER);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_RTCW_FOLDER || resultCode != RESULT_OK || data == null) {
            return;
        }

        Uri tree = data.getData();
        if (tree == null) {
            showFatal("No folder was selected.");
            return;
        }

        try {
            getContentResolver().takePersistableUriPermission(
                    tree, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException ignored) {
        }

        try {
            importRequiredFiles(tree);
        } catch (Exception e) {
            showFatal("Failed to import RTCW data:\n" + e.getMessage());
            return;
        }

        if (!hasRequiredData()) {
            showFatal(
                    "The selected folder does not contain the complete RTCW data set.\n\n" +
                    "Required: pak0.pk3, sp_pak1.pk3, sp_pak2.pk3, sp_pak3.pk3, " +
                    "sp_pak4.pk3, sp_rend2_shaders0.pk3"
            );
            return;
        }

        showReady();
    }

    private void showReady() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        box.setPadding(pad, pad, pad, pad);

        TextView text = new TextView(this);
        text.setText(
                "DarkWolf RTCW Rend2\n\n" +
                "RTCW game data: READY\n" +
                "Runtime mode: QVM bytecode\n" +
                "Test map: escape1\n\n" +
                "Tap START GAME. If the game closes or remains black, reopen this launcher " +
                "and tap SHOW LAST STARTUP LOG."
        );
        text.setTextSize(18f);

        Button startButton = new Button(this);
        startButton.setText("START GAME");
        startButton.setOnClickListener(v -> launchGame());

        Button importButton = new Button(this);
        importButton.setText("REIMPORT RTCW PK3 FOLDER");
        importButton.setOnClickListener(v -> openFolderPicker());

        Button logButton = new Button(this);
        logButton.setText("SHOW LAST STARTUP LOG");
        logButton.setOnClickListener(v -> showLastLog());

        box.addView(text);
        box.addView(startButton);
        box.addView(importButton);
        box.addView(logButton);
        setContentView(box);
    }

    private void importRequiredFiles(Uri tree) throws IOException {
        ContentResolver resolver = getContentResolver();
        String treeId = DocumentsContract.getTreeDocumentId(tree);
        Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(tree, treeId);
        Map<String, Uri> found = new HashMap<>();

        try (Cursor cursor = resolver.query(
                children,
                new String[] {
                        DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                        DocumentsContract.Document.COLUMN_DISPLAY_NAME
                },
                null, null, null)) {
            if (cursor == null) {
                throw new IOException("Cannot read selected folder.");
            }

            int idCol = cursor.getColumnIndexOrThrow(
                    DocumentsContract.Document.COLUMN_DOCUMENT_ID);
            int nameCol = cursor.getColumnIndexOrThrow(
                    DocumentsContract.Document.COLUMN_DISPLAY_NAME);

            while (cursor.moveToNext()) {
                String name = cursor.getString(nameCol);
                String docId = cursor.getString(idCol);
                if (name != null && docId != null) {
                    found.put(name.toLowerCase(Locale.ROOT),
                            DocumentsContract.buildDocumentUriUsingTree(tree, docId));
                }
            }
        }

        byte[] buffer = new byte[256 * 1024];
        for (String required : REQUIRED) {
            Uri source = found.get(required.toLowerCase(Locale.ROOT));
            if (source == null) {
                continue;
            }

            File target = new File(retailMain, required);
            File temp = new File(retailMain, required + ".importing");
            try (InputStream in = resolver.openInputStream(source);
                 FileOutputStream out = new FileOutputStream(temp, false)) {
                if (in == null) {
                    throw new IOException("Cannot open " + required);
                }
                int count;
                while ((count = in.read(buffer)) > 0) {
                    out.write(buffer, 0, count);
                }
                out.getFD().sync();
            }

            if (target.exists() && !target.delete()) {
                throw new IOException("Cannot replace " + required);
            }
            if (!temp.renameTo(target)) {
                throw new IOException("Cannot install " + required);
            }
        }
    }

    private boolean hasRequiredData() {
        for (String name : REQUIRED) {
            File file = new File(retailMain, name);
            if (!file.isFile() || file.length() <= 0) {
                return false;
            }
        }
        return true;
    }

    private void launchGame() {
        Intent intent = new Intent(this, DarkWolfActivity.class);
        startActivity(intent);
        finish();
    }

    private void showLastLog() {
        File log = new File(retailMain, "rtcwconsole.log");
        if (!log.isFile()) {
            showFatal("No startup log exists yet.");
            return;
        }
        try {
            byte[] data = new byte[(int)Math.min(log.length(), 64 * 1024)];
            try (java.io.RandomAccessFile raf = new java.io.RandomAccessFile(log, "r")) {
                long start = Math.max(0, log.length() - data.length);
                raf.seek(start);
                raf.readFully(data);
            }
            String text = new String(data, "UTF-8");
            new AlertDialog.Builder(this)
                    .setTitle("DarkWolf startup log")
                    .setMessage(text)
                    .setPositiveButton("OK", null)
                    .show();
        } catch (Exception e) {
            showFatal("Cannot read startup log:\n" + e.getMessage());
        }
    }

    private void showFatal(String message) {
        new AlertDialog.Builder(this)
                .setTitle("DarkWolf RTCW Rend2")
                .setMessage(message)
                .setPositiveButton("OK", null)
                .show();
    }
}
EOF

cat > "$PROJECT/app/src/main/java/org/darkwolf/rend2/DarkWolfActivity.java" <<'EOF'
package org.darkwolf.rend2;

import android.os.Bundle;
import android.util.Log;
import org.libsdl.app.SDLActivity;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

public final class DarkWolfActivity extends SDLActivity {
    private static final String TAG = "DarkWolfRTCW";
    private File homeRoot;
    private File retailRoot;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        prepareFilesystem();
        super.onCreate(savedInstanceState);
    }

    private void prepareFilesystem() {
        homeRoot = new File(getFilesDir(), "DarkWolfRTCW");
        File external = getExternalFilesDir(null);
        retailRoot = external != null
                ? new File(external, "DarkWolfRTCW")
                : homeRoot;

        File homeMain = new File(homeRoot, "main");
        File retailMain = new File(retailRoot, "main");
        if (!homeMain.mkdirs() && !homeMain.isDirectory()) {
            throw new IllegalStateException("Cannot create " + homeMain);
        }
        if (!retailMain.mkdirs() && !retailMain.isDirectory()) {
            throw new IllegalStateException("Cannot create " + retailMain);
        }

        try {
            copyAsset("darkwolf-runtime/main/cgame.sp.arm64.so",
                    new File(homeMain, "cgame.sp.arm64.so"));
            copyAsset("darkwolf-runtime/main/qagame.sp.arm64.so",
                    new File(homeMain, "qagame.sp.arm64.so"));
            copyAsset("darkwolf-runtime/main/ui.sp.arm64.so",
                    new File(homeMain, "ui.sp.arm64.so"));
            writeInstallHint(retailRoot, retailMain);
        } catch (IOException e) {
            throw new IllegalStateException("DarkWolf Android filesystem bootstrap failed", e);
        }

        Log.i(TAG, "A5_HOME=" + homeRoot.getAbsolutePath());
        Log.i(TAG, "A5_RETAIL_BASE=" + retailRoot.getAbsolutePath());
        Log.i(TAG, "A5_RETAIL_MAIN=" + retailMain.getAbsolutePath());
    }

    private void copyAsset(String assetName, File target) throws IOException {
        File tmp = new File(target.getParentFile(), target.getName() + ".tmp");
        try (InputStream in = getAssets().open(assetName);
             FileOutputStream out = new FileOutputStream(tmp, false)) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) {
                out.write(buffer, 0, n);
            }
            out.getFD().sync();
        }
        if (target.exists() && !target.delete()) {
            throw new IOException("Cannot replace " + target);
        }
        if (!tmp.renameTo(target)) {
            throw new IOException("Cannot install " + target);
        }
        target.setReadable(true, true);
        target.setExecutable(true, true);
    }

    private void writeInstallHint(File base, File main) throws IOException {
        File hint = new File(base, "INSTALL_RTCW_DATA_HERE.txt");
        String message =
                "DarkWolf RTCW Rend2 Android\n" +
                "Copy your legally owned Return to Castle Wolfenstein retail PK3 files into:\n" +
                main.getAbsolutePath() + "\n" +
                "Expected directory name is lowercase: main\n" +
                "The application never bundles or downloads retail game data.\n";
        try (FileOutputStream out = new FileOutputStream(hint, false)) {
            out.write(message.getBytes("UTF-8"));
        }
    }

    @Override
    protected String[] getArguments() {
        if (homeRoot == null || retailRoot == null) {
            prepareFilesystem();
        }
        return new String[] {
                "+set", "fs_basepath", retailRoot.getAbsolutePath(),
                "+set", "fs_homepath", retailRoot.getAbsolutePath(),
                "+set", "fs_game", "",
                "+set", "vm_cgame", "1",
                "+set", "vm_game", "1",
                "+set", "vm_ui", "1",
                "+set", "com_introplayed", "1",
                "+set", "logfile", "2",
                "+set", "developer", "1",
                "+set", "r_ext_texture_filter_anisotropic", "0",
                "+set", "r_fullscreen", "0",
                "+spdevmap", "escape1"
        };
    }
}
EOF

cat > "$PROJECT/app/src/main/AndroidManifest.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-feature android:glEsVersion="0x00030000" android:required="true" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
    <uses-feature android:name="android.hardware.gamepad" android:required="false" />
    <uses-feature android:name="android.hardware.usb.host" android:required="false" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.VIBRATE" />

    <application
        android:label="DarkWolf RTCW Rend2"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="false"
        android:extractNativeLibs="true"
        android:hardwareAccelerated="true"
        android:largeHeap="true"
        android:theme="@style/AppTheme">
        <activity
            android:name="org.darkwolf.rend2.LauncherActivity"
            android:label="DarkWolf RTCW Rend2"
            android:screenOrientation="sensorLandscape"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <activity
            android:name="org.darkwolf.rend2.DarkWolfActivity"
            android:label="DarkWolf RTCW Rend2"
            android:alwaysRetainTaskState="true"
            android:launchMode="singleTop"
            android:screenOrientation="sensorLandscape"
            android:configChanges="layoutDirection|locale|orientation|uiMode|screenLayout|screenSize|smallestScreenSize|keyboard|keyboardHidden|navigation"
            android:preferMinimalPostProcessing="true"
            android:exported="false" />
    </application>
</manifest>
EOF

cp "$RUNTIME/bin/libmain.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"
cp "$RUNTIME/bin/libSDL2.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"

CXX_SHARED="$(find "$NDK" -type f -path '*/aarch64-linux-android/libc++_shared.so' -print -quit)"
test -s "$CXX_SHARED"
cp "$CXX_SHARED" "$PROJECT/app/src/main/jniLibs/arm64-v8a/libc++_shared.so"

cp "$MODULES/bin/cgame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"
cp "$MODULES/bin/qagame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"
cp "$MODULES/bin/ui.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"

cat > "$PROJECT/app/src/main/assets/darkwolf-runtime/PROVENANCE.txt" <<EOF
BASE_RUN_ID=37266797451
BASE_HEAD_SHA=e410db87b5704fb1518740f1cfc760e9ea67d34f
ANDROID_BRANCH=rend2-android-testlab-v0.1
ANDROID_ABI=arm64-v8a
ANDROID_MIN_API=29
RENDERER=Rend2
GPU_API=OpenGL_ES_3.x
A3_NATIVE_RUNTIME_SHA256=$(sha256sum "$RUNTIME/bin/libmain.so" | awk '{print $1}')
A3_SDL2_SHA256=$(sha256sum "$RUNTIME/bin/libSDL2.so" | awk '{print $1}')
EOF

(
  cd "$PROJECT"
  ./gradlew --no-daemon --stacktrace :app:assembleDebug
)

built="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
test -s "$built"
cp "$built" "$DIST/$APK_NAME"

unzip -l "$DIST/$APK_NAME" | tee "$OUT/apk-contents.txt"
grep -F 'lib/arm64-v8a/libmain.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'lib/arm64-v8a/libSDL2.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'lib/arm64-v8a/libc++_shared.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/cgame.sp.arm64.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/qagame.sp.arm64.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/ui.sp.arm64.so' "$OUT/apk-contents.txt" >/dev/null
if grep -E 'lib/(armeabi-v7a|x86|x86_64)/' "$OUT/apk-contents.txt" >/dev/null; then
  echo "Unexpected non-arm64 ABI in APK" >&2
  exit 1
fi

if command -v apksigner >/dev/null 2>&1; then
  apksigner verify --verbose "$DIST/$APK_NAME" | tee "$OUT/apksigner.txt"
else
  jarsigner -verify "$DIST/$APK_NAME" | tee "$OUT/apksigner.txt"
fi

sha256sum "$DIST/$APK_NAME" | tee "$DIST/$APK_NAME.sha256"

cat > "$OUT/A4_BOOTSTRAP_AUDIT.txt" <<EOF
A4_APK_BOOTSTRAP=PASS
APK=$APK_NAME
APPLICATION_ID=org.darkwolf.rend2
ABI=arm64-v8a
MIN_SDK=29
TARGET_SDK=35
GLES_REQUIRED=3.0
SDL_MAIN_EXPORT=PASS
REND2_NATIVE_RUNTIME=PACKAGED
NATIVE_GAME_MODULES=PACKAGED_AS_A5_ASSETS
A5_ACTIVITY=org.darkwolf.rend2.LauncherActivity
A5_GAME_ACTIVITY=org.darkwolf.rend2.DarkWolfActivity
PHONE_FIRST_DATA_IMPORTER=SAF_DOCUMENT_TREE
PHONE_FIRST_AUTO_MAP=escape1
PHONE_FIRST_VM_MODE=QVM_BYTECODE
PHONE_FIRST_VM_CGAME=1
PHONE_FIRST_VM_GAME=1
PHONE_FIRST_VM_UI=1
PHONE_FIRST_LOGFILE=2
PHONE_FIRST_READY_SCREEN=START_GAME_REIMPORT_LOG
A5_BASEGAME_CASE=main
A5_FS_BASEPATH=APP_SCOPED_EXTERNAL_DARKWOLF_ROOT
A5_FS_HOMEPATH=APP_PRIVATE_DARKWOLF_ROOT
A5_NATIVE_MODULE_EXTRACTION=PASS_BY_JAVA_COMPILE_AND_APK_CONTENT
RETAIL_GAME_DATA=NOT_BUNDLED
EOF

cat "$OUT/A4_BOOTSTRAP_AUDIT.txt"
