#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SDL="$WORKDIR/SDL2"
RUNTIME="$WORKDIR/native-runtime-x86_64"
MODULES="$WORKDIR/game-modules-x86_64"
QVMS="$WORKDIR/game-qvms"
OUT="$WORKDIR/android-apk"
PROJECT="$OUT/project"
DIST="$OUT/dist"
NDK="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
TOOL="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
APK_NAME="DarkWolf-ioRTCW-Rend2-Android-v0.1-X86_64-CI-Debug.apk"

test -s "$RUNTIME/bin/libmain.so"
test -s "$RUNTIME/bin/libSDL2.so"
test -s "$MODULES/bin/cgame.sp.x86_64.so"
test -s "$MODULES/bin/qagame.sp.x86_64.so"
test -s "$MODULES/bin/ui.sp.x86_64.so"
test -s "$QVMS/bin/ui.sp.qvm"
test -s "$QVMS/bin/cgame.sp.qvm"
test -s "$QVMS/bin/qagame.sp.qvm"
test -d "$SDL/android-project"

# Do not use grep -q here under pipefail: llvm-nm can see SIGPIPE and return 74.
"$TOOL/llvm-nm" -D --defined-only "$RUNTIME/bin/libmain.so" > "$WORKDIR/a4-libmain-symbols.txt"
grep -E '[[:space:]]SDL_main$' "$WORKDIR/a4-libmain-symbols.txt" >/dev/null
echo "A4_SDL_MAIN_EXPORT=PASS"

rm -rf "$OUT"
mkdir -p "$PROJECT/app/src/main/java" "$PROJECT/app/src/main/res" \
  "$PROJECT/app/src/main/jniLibs/x86_64" \
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
            abiFilters 'x86_64'
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
            copyAsset("darkwolf-runtime/main/cgame.sp.x86_64.so",
                    new File(homeMain, "cgame.sp.x86_64.so"));
            copyAsset("darkwolf-runtime/main/qagame.sp.x86_64.so",
                    new File(homeMain, "qagame.sp.x86_64.so"));
            copyAsset("darkwolf-runtime/main/ui.sp.x86_64.so",
                    new File(homeMain, "ui.sp.x86_64.so"));

            File vmDir = new File(retailMain, "vm");
            if (!vmDir.mkdirs() && !vmDir.isDirectory()) {
                throw new IOException("Cannot create " + vmDir);
            }
            copyAsset("darkwolf-runtime/main/vm/ui.sp.qvm",
                    new File(vmDir, "ui.sp.qvm"));
            copyAsset("darkwolf-runtime/main/vm/cgame.sp.qvm",
                    new File(vmDir, "cgame.sp.qvm"));
            copyAsset("darkwolf-runtime/main/vm/qagame.sp.qvm",
                    new File(vmDir, "qagame.sp.qvm"));
            Log.i(TAG, "A6_QVM_DIR=" + vmDir.getAbsolutePath());
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
                "+set", "fs_homepath", homeRoot.getAbsolutePath(),
                "+set", "fs_game", "",
                "+set", "vm_cgame", "1",
                "+set", "vm_game", "1",
                "+set", "vm_ui", "1",
                "+set", "dw_android_ci_playerstart", "1",
                "+set", "com_introplayed", "1",
                "+set", "r_fullscreen", "0",
                "+set", "r_mode", "-1",
                "+set", "r_customwidth", "640",
                "+set", "r_customheight", "360",
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
            android:name="org.darkwolf.rend2.DarkWolfActivity"
            android:label="DarkWolf RTCW Rend2"
            android:alwaysRetainTaskState="true"
            android:launchMode="singleTop"
            android:screenOrientation="sensorLandscape"
            android:configChanges="layoutDirection|locale|orientation|uiMode|screenLayout|screenSize|smallestScreenSize|keyboard|keyboardHidden|navigation"
            android:preferMinimalPostProcessing="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

cp "$RUNTIME/bin/libmain.so" "$PROJECT/app/src/main/jniLibs/x86_64/"
cp "$RUNTIME/bin/libSDL2.so" "$PROJECT/app/src/main/jniLibs/x86_64/"

CXX_SHARED="$(find "$NDK" -type f -path '*/x86_64-linux-android/libc++_shared.so' -print -quit)"
test -s "$CXX_SHARED"
cp "$CXX_SHARED" "$PROJECT/app/src/main/jniLibs/x86_64/libc++_shared.so"

cp "$MODULES/bin/cgame.sp.x86_64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"
cp "$MODULES/bin/qagame.sp.x86_64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"
cp "$MODULES/bin/ui.sp.x86_64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/"
mkdir -p "$PROJECT/app/src/main/assets/darkwolf-runtime/main/vm"
cp "$QVMS/bin/ui.sp.qvm" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/vm/"
cp "$QVMS/bin/cgame.sp.qvm" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/vm/"
cp "$QVMS/bin/qagame.sp.qvm" "$PROJECT/app/src/main/assets/darkwolf-runtime/main/vm/"

cat > "$PROJECT/app/src/main/assets/darkwolf-runtime/PROVENANCE.txt" <<EOF
BASE_RUN_ID=37266797451
BASE_HEAD_SHA=e410db87b5704fb1518740f1cfc760e9ea67d34f
ANDROID_BRANCH=rend2-android-testlab-v0.1
ANDROID_ABI=x86_64
ANDROID_MIN_API=29
RENDERER=Rend2
GPU_API=OpenGL_ES_3.x
A3_NATIVE_RUNTIME_SHA256=$(sha256sum "$RUNTIME/bin/libmain.so" | awk '{print $1}')
A3_SDL2_SHA256=$(sha256sum "$RUNTIME/bin/libSDL2.so" | awk '{print $1}')
A6_QVM_UI_SHA256=$(sha256sum "$QVMS/bin/ui.sp.qvm" | awk '{print $1}')
A6_QVM_CGAME_SHA256=$(sha256sum "$QVMS/bin/cgame.sp.qvm" | awk '{print $1}')
A6_QVM_QAGAME_SHA256=$(sha256sum "$QVMS/bin/qagame.sp.qvm" | awk '{print $1}')
EOF

(
  cd "$PROJECT"
  ./gradlew --no-daemon --stacktrace :app:assembleDebug
)

built="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
test -s "$built"
cp "$built" "$DIST/$APK_NAME"

unzip -l "$DIST/$APK_NAME" | tee "$OUT/apk-contents.txt"
grep -F 'lib/x86_64/libmain.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'lib/x86_64/libSDL2.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'lib/x86_64/libc++_shared.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/cgame.sp.x86_64.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/qagame.sp.x86_64.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/ui.sp.x86_64.so' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/vm/ui.sp.qvm' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/vm/cgame.sp.qvm' "$OUT/apk-contents.txt" >/dev/null
grep -F 'assets/darkwolf-runtime/main/vm/qagame.sp.qvm' "$OUT/apk-contents.txt" >/dev/null
if grep -E 'lib/(armeabi-v7a|arm64-v8a|x86)/' "$OUT/apk-contents.txt" >/dev/null; then
  echo "Unexpected non-x86_64 ABI in CI APK" >&2
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
ABI=x86_64
MIN_SDK=29
TARGET_SDK=35
GLES_REQUIRED=3.0
SDL_MAIN_EXPORT=PASS
REND2_NATIVE_RUNTIME=PACKAGED
NATIVE_GAME_MODULES=PACKAGED_AS_A5_ASSETS
EXACT_SOURCE_SP_QVMS=PACKAGED_AND_EXTRACTED_TO_RETAIL_MAIN_VM
VM_CGAME=1
VM_GAME=1
VM_UI=1
A5_ACTIVITY=org.darkwolf.rend2.DarkWolfActivity
A5_BASEGAME_CASE=main
A5_FS_BASEPATH=APP_SCOPED_EXTERNAL_DARKWOLF_ROOT
A5_FS_HOMEPATH=APP_PRIVATE_DARKWOLF_ROOT
A5_NATIVE_MODULE_EXTRACTION=PASS_BY_JAVA_COMPILE_AND_APK_CONTENT
RETAIL_GAME_DATA=NOT_BUNDLED
EOF

cat "$OUT/A4_BOOTSTRAP_AUDIT.txt"
