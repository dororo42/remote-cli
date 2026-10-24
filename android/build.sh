#!/usr/bin/env bash
# Builds dist/RemoteCli-Android-android6.apk on Linux (CI) — the bash twin of build.ps1, which stays
# the official build on the Windows machine. Needs a JDK 11+, and an Android SDK with
# build-tools 36.0.0 and platforms/android-36 (the GitHub runner has both after sdkmanager).
# The signing key arrives from repository secrets (ANDROID6_KEYSTORE_B64 + ANDROID6_KEY_PASSWORD):
# the same key every run, so a new APK installs over the previous one. Local runs may pass the same
# environment, or ANDROID6_KEYSTORE (a path) instead of the base64 variable.
set -euo pipefail
cd "$(dirname "$0")"

: "${ANDROID_HOME:?set ANDROID_HOME (the CI runner provides it)}"
build_tools="$ANDROID_HOME/build-tools/36.0.0"
android_jar="$ANDROID_HOME/platforms/android-36/android.jar"
for tool in "$build_tools/aapt2" "$build_tools/zipalign" "$build_tools/lib/apksigner.jar" "$android_jar"; do
    [ -f "$tool" ] || { echo "missing build tool: $tool" >&2; exit 1; }
done
java_bin="${JAVA_HOME:+$JAVA_HOME/bin/}java"
command -v javac >/dev/null || { echo "javac not on PATH (set JAVA_HOME)" >&2; exit 1; }

build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT
mkdir -p "$build/classes" "$build/generated" "$build/dex" ../dist

# The QR reader (ZXing core, Apache-2.0) comes from Maven Central once and is checked against a known hash.
zxing="../.cache/zxing-core-3.5.3.jar"
if [ ! -f "$zxing" ]; then
    mkdir -p "$(dirname "$zxing")"
    curl -fsSL --retry 2 -o "$zxing" 'https://repo1.maven.org/maven2/com/google/zxing/core/3.5.3/core-3.5.3.jar'
fi
echo '8d8064c1636fdaef7189dd9055c7d59950a8940a12f2293956446ec3c109fd82  '"$zxing" | sha256sum -c - >/dev/null

"$build_tools/aapt2" compile --dir res -o "$build/resources.zip"
"$build_tools/aapt2" link -o "$build/unsigned.apk" -I "$android_jar" --manifest AndroidManifest.xml --java "$build/generated" "$build/resources.zip"
mapfile -t sources < <(find src "$build/generated" -name '*.java')
javac -J-Duser.language=en -Xlint:-options --release 8 -encoding UTF-8 \
    -classpath "$android_jar:$zxing" -d "$build/classes" "${sources[@]}"
jar cf "$build/classes.jar" -C "$build/classes" .
"$java_bin" -cp "$build_tools/lib/d8.jar" com.android.tools.r8.D8 --lib "$android_jar" --min-api 23 \
    --output "$build/dex" "$build/classes.jar" "$zxing"
(cd "$build/dex" && zip -q -j "$build/unsigned.apk" classes.dex)

# The key: base64 of the PKCS12 store from the repository secrets. A run without it cannot produce an
# APK that installs over the previous one, so it is refused rather than minting a throwaway identity.
keystore="$build/signing.p12"
if [ -n "${ANDROID6_KEYSTORE_B64:-}" ]; then
    printf '%s' "$ANDROID6_KEYSTORE_B64" | base64 -d > "$keystore"
elif [ -n "${ANDROID6_KEYSTORE:-}" ]; then
    cp "$ANDROID6_KEYSTORE" "$keystore"
else
    echo 'missing signing key: set ANDROID6_KEYSTORE_B64 (and ANDROID6_KEY_PASSWORD) in the repository secrets' >&2
    exit 1
fi
: "${ANDROID6_KEY_PASSWORD:?set ANDROID6_KEY_PASSWORD in the repository secrets}"
export REMOTECLI_SIGN_PASSWORD="$ANDROID6_KEY_PASSWORD"

apk=../dist/RemoteCli-Android-android6.apk
"$build_tools/zipalign" -f -p 4 "$build/unsigned.apk" "$build/aligned.apk"
"$java_bin" -jar "$build_tools/lib/apksigner.jar" sign --ks "$keystore" --ks-key-alias remotecli \
    --ks-pass env:REMOTECLI_SIGN_PASSWORD --out "$apk" "$build/aligned.apk"
"$java_bin" -jar "$build_tools/lib/apksigner.jar" verify "$apk"
"$build_tools/zipalign" -c 4 "$apk"
echo "RemoteCli-Android-android6.apk  $(stat -c %s "$apk") bytes  sha256 $(sha256sum "$apk" | cut -d' ' -f1)"
