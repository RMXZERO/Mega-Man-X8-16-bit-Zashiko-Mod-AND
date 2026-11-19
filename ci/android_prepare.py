#!/usr/bin/env python3
"""Android 빌드 전처리 (멱등). 저장소 루트에서 실행.

iOS 전처리(ios_prepare.py)의 공통 부분을 재사용하고 Android 전용 처리만 추가한다.

1) System/CharacterManager.gd : Android 에서 터치 컨트롤을 기본으로 켬
   (원본은 touch_controls 변수가 항상 false 라 Android 에서도 터치 UI 가 안 뜸).
   블루투스/USB 게임패드가 연결돼 있으면 터치 UI 를 켜지 않음
2) System/Character_Spawner.gd: 존재하지 않는 TouchControl.gd 경로 수정 (ios_prepare 와 동일)
3) project.godot             : Android(GLES3)용 ETC2 텍스처 임포트 활성화
4) export_presets.cfg        : "Android CI" 프리셋 추가 (arm64, 서명은 환경변수로 받음)
5) ko-assets/                : 한글 번역/폰트 덮어쓰기 + 번역 목록에 ko 추가 (ios_prepare 와 동일)

환경변수: PACKAGE_NAME, APP_DISPLAY_NAME, KEYSTORE_PATH, KEYSTORE_USER,
          KEYSTORE_PASS, VERSION_CODE
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ios_prepare as ios  # read/write/patch_spawner/apply_korean 재사용

PACKAGE_NAME = os.environ.get("PACKAGE_NAME", "com.mmx8.android")
APP_NAME = os.environ.get("APP_DISPLAY_NAME", "MMX8 Zashiko-Mod")
KEYSTORE_PATH = os.environ.get("KEYSTORE_PATH", "")
KEYSTORE_USER = os.environ.get("KEYSTORE_USER", "")
KEYSTORE_PASS = os.environ.get("KEYSTORE_PASS", "")
VERSION_CODE = os.environ.get("VERSION_CODE", "1")
PRESET_NAME = "Android CI"


def patch_character_manager():
    path = "System/CharacterManager.gd"
    src = ios.read(path)
    if "# ANDROID-PORT" in src:
        print(f"[skip] {path} (이미 패치됨)")
        return
    nl = "\r\n" if "\r\n" in src else "\n"
    pat = re.compile(
        r"func is_Android\(\) -> bool:\s*\n\s*if OS\.get_name\(\) == \"Android\":\s*\n\s*return true\s*\n\s*return false\s*\n"
        r"func touch_controls_enabled\(\) -> bool:\s*\n\s*if is_Android\(\):\s*\n\s*return touch_controls\s*\n\s*return false",
        re.M,
    )
    new = nl.join([
        "# ANDROID-PORT: Android 에서는 터치 컨트롤 기본 사용, 게임패드가 연결돼 있으면 사용 안 함",
        "func is_Android() -> bool:",
        "\treturn OS.get_name() == \"Android\"",
        "func touch_controls_enabled() -> bool:",
        "\tif not is_Android():",
        "\t\treturn false",
        "\tfor _id in Input.get_connected_joypads():",
        "\t\tif not (Input.get_joy_name(_id) in [\"uinput-fpc\", \"uinput-fortsense\", \"uinput-hidraw\"]):",
        "\t\t\treturn false",
        "\treturn true",
    ])
    out, n = pat.subn(lambda m: new, src, count=1)
    if n != 1:
        sys.exit(f"[error] {path}: is_Android 블록을 찾지 못함 (소스가 바뀌었는지 확인)")
    ios.write(path, out)
    print(f"[ok]   {path}")


def patch_project_godot():
    path = "project.godot"
    src = ios.read(path)
    nl = "\r\n" if "\r\n" in src else "\n"
    m = re.search(r"^\[rendering\]\s*$", src, re.M)
    if not m:
        sys.exit("[error] project.godot에 [rendering] 섹션이 없음")
    if "vram_compression/import_etc2" in src:
        print("[skip] project.godot (ETC2 이미 설정됨)")
        return
    src = src[: m.end()] + nl + "vram_compression/import_etc2=true" + src[m.end():]
    ios.write(path, src)
    print("[ok]   project.godot += vram_compression/import_etc2=true")


PRESET = """
[preset.{n}]

name="{name}"
platform="Android"
runnable=true
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter="*.ase, *.aseprite, *.pdn, *.csv, *.txt, *.md, *.zip, *.dll, *.exe, *.ico, *.gif, *.world"
export_path=""
script_export_mode=1
script_encryption_key=""

[preset.{n}.options]

custom_template/debug=""
custom_template/release=""
custom_build/use_custom_build=false
architectures/armeabi-v7a=false
architectures/arm64-v8a=true
architectures/x86=false
architectures/x86_64=false
keystore/debug=""
keystore/debug_user=""
keystore/debug_password=""
keystore/release="{ks}"
keystore/release_user="{ks_user}"
keystore/release_password="{ks_pass}"
version/code={vcode}
version/name="1.2"
package/unique_name="{pkg}"
package/name="{app}"
package/signed=true
package/classify_as_game=true
package/retain_data_on_uninstall=false
package/exclude_from_recents=false
screen/immersive_mode=true
screen/support_small=true
screen/support_normal=true
screen/support_large=true
screen/support_xlarge=true
user_data_backup/allow=false
"""


def patch_presets():
    path = "export_presets.cfg"
    src = ios.read(path) if os.path.exists(path) else ""
    if re.search(r'^name="%s"' % re.escape(PRESET_NAME), src, re.M):
        print(f'[skip] export_presets.cfg ("{PRESET_NAME}" 이미 있음)')
        return
    nums = [int(x) for x in re.findall(r"^\[preset\.(\d+)\]", src, re.M)]
    n = (max(nums) + 1) if nums else 0
    nl = "\r\n" if "\r\n" in src else "\n"
    block = PRESET.format(
        n=n, name=PRESET_NAME, pkg=PACKAGE_NAME, app=APP_NAME, vcode=VERSION_CODE,
        ks=KEYSTORE_PATH, ks_user=KEYSTORE_USER, ks_pass=KEYSTORE_PASS,
    ).replace("\n", nl)
    ios.write(path, src.rstrip() + nl + block)
    print(f"[ok]   export_presets.cfg += preset.{n} ({PRESET_NAME})")


if __name__ == "__main__":
    if not os.path.exists("project.godot"):
        sys.exit("[error] 저장소 루트(project.godot가 있는 곳)에서 실행하세요")
    patch_character_manager()
    ios.patch_spawner()
    patch_project_godot()
    patch_presets()
    ios.apply_korean()
