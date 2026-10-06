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

# SDLActivity calls SDL_main by name. Prove our ioRTCW entry point is exported
# before spending time on Gradle packaging.
"$TOOL/llvm-readelf" -Ws "$RUNTIME/bin/libmain.so" > "$WORKDIR/a4-libmain-symbols.txt"
if ! grep -Eq '[[:space:]]SDL_main

rm -rf "$OUT"
mkdir -p "$PROJECT/app/src/main/java" "$PROJECT/app/src/main/res" \
  "$PROJECT/app/src/main/jniLibs/arm64-v8a" \
  "$PROJECT/app/src/main/assets/darkwolf-runtime/Main" "$DIST"

cp -a "$SDL/android-project/app/src/main/java/org" "$PROJECT/app/src/main/java/"
cp -a "$SDL/android-project/app/src/main/res/." "$PROJECT/app/src/main/res/"
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
        release {
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
            android:name="org.libsdl.app.SDLActivity"
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

cp "$RUNTIME/bin/libmain.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"
cp "$RUNTIME/bin/libSDL2.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"

CXX_SHARED="$(find "$NDK" -type f -path '*/aarch64-linux-android/libc++_shared.so' -print -quit)"
test -s "$CXX_SHARED"
cp "$CXX_SHARED" "$PROJECT/app/src/main/jniLibs/arm64-v8a/libc++_shared.so"

# Preserve the native modules inside the bootstrap APK already. A5 will add the
# controlled extraction/data-discovery layer rather than rebuilding them.
cp "$MODULES/bin/cgame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/qagame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/ui.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"

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

# Package-content gates: no accidental multi-ABI or OpenGL1 substitution.
unzip -l "$DIST/$APK_NAME" | tee "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libmain.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libSDL2.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libc++_shared.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/cgame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/qagame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/ui.sp.arm64.so' "$OUT/apk-contents.txt"
! grep -Eq 'lib/(armeabi-v7a|x86|x86_64)/' "$OUT/apk-contents.txt"

# APK is debug-signed by AGP. Verify structure/signature and emit deterministic evidence.
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
RETAIL_GAME_DATA=NOT_BUNDLED
EOF

cat "$OUT/A4_BOOTSTRAP_AUDIT.txt"
 "$WORKDIR/a4-libmain-symbols.txt"; then
  echo "A4 gate: SDL_main export missing; main-like exports follow:" >&2
  grep -E '[[:space:]](SDL_main|main)

rm -rf "$OUT"
mkdir -p "$PROJECT/app/src/main/java" "$PROJECT/app/src/main/res" \
  "$PROJECT/app/src/main/jniLibs/arm64-v8a" \
  "$PROJECT/app/src/main/assets/darkwolf-runtime/Main" "$DIST"

cp -a "$SDL/android-project/app/src/main/java/org" "$PROJECT/app/src/main/java/"
cp -a "$SDL/android-project/app/src/main/res/." "$PROJECT/app/src/main/res/"
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
        release {
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
            android:name="org.libsdl.app.SDLActivity"
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

cp "$RUNTIME/bin/libmain.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"
cp "$RUNTIME/bin/libSDL2.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"

CXX_SHARED="$(find "$NDK" -type f -path '*/aarch64-linux-android/libc++_shared.so' -print -quit)"
test -s "$CXX_SHARED"
cp "$CXX_SHARED" "$PROJECT/app/src/main/jniLibs/arm64-v8a/libc++_shared.so"

# Preserve the native modules inside the bootstrap APK already. A5 will add the
# controlled extraction/data-discovery layer rather than rebuilding them.
cp "$MODULES/bin/cgame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/qagame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/ui.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"

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

# Package-content gates: no accidental multi-ABI or OpenGL1 substitution.
unzip -l "$DIST/$APK_NAME" | tee "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libmain.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libSDL2.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libc++_shared.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/cgame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/qagame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/ui.sp.arm64.so' "$OUT/apk-contents.txt"
! grep -Eq 'lib/(armeabi-v7a|x86|x86_64)/' "$OUT/apk-contents.txt"

# APK is debug-signed by AGP. Verify structure/signature and emit deterministic evidence.
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
RETAIL_GAME_DATA=NOT_BUNDLED
EOF

cat "$OUT/A4_BOOTSTRAP_AUDIT.txt"
 "$WORKDIR/a4-libmain-symbols.txt" >&2 || true
  exit 1
fi
echo "A4_SDL_MAIN_EXPORT=PASS"

rm -rf "$OUT"
mkdir -p "$PROJECT/app/src/main/java" "$PROJECT/app/src/main/res" \
  "$PROJECT/app/src/main/jniLibs/arm64-v8a" \
  "$PROJECT/app/src/main/assets/darkwolf-runtime/Main" "$DIST"

cp -a "$SDL/android-project/app/src/main/java/org" "$PROJECT/app/src/main/java/"
cp -a "$SDL/android-project/app/src/main/res/." "$PROJECT/app/src/main/res/"
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
        release {
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
            android:name="org.libsdl.app.SDLActivity"
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

cp "$RUNTIME/bin/libmain.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"
cp "$RUNTIME/bin/libSDL2.so" "$PROJECT/app/src/main/jniLibs/arm64-v8a/"

CXX_SHARED="$(find "$NDK" -type f -path '*/aarch64-linux-android/libc++_shared.so' -print -quit)"
test -s "$CXX_SHARED"
cp "$CXX_SHARED" "$PROJECT/app/src/main/jniLibs/arm64-v8a/libc++_shared.so"

# Preserve the native modules inside the bootstrap APK already. A5 will add the
# controlled extraction/data-discovery layer rather than rebuilding them.
cp "$MODULES/bin/cgame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/qagame.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"
cp "$MODULES/bin/ui.sp.arm64.so" "$PROJECT/app/src/main/assets/darkwolf-runtime/Main/"

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

# Package-content gates: no accidental multi-ABI or OpenGL1 substitution.
unzip -l "$DIST/$APK_NAME" | tee "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libmain.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libSDL2.so' "$OUT/apk-contents.txt"
grep -Fq 'lib/arm64-v8a/libc++_shared.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/cgame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/qagame.sp.arm64.so' "$OUT/apk-contents.txt"
grep -Fq 'assets/darkwolf-runtime/Main/ui.sp.arm64.so' "$OUT/apk-contents.txt"
! grep -Eq 'lib/(armeabi-v7a|x86|x86_64)/' "$OUT/apk-contents.txt"

# APK is debug-signed by AGP. Verify structure/signature and emit deterministic evidence.
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
RETAIL_GAME_DATA=NOT_BUNDLED
EOF

cat "$OUT/A4_BOOTSTRAP_AUDIT.txt"
