#!/usr/bin/env python3
"""
Constructeur de l'installateur autonome Windows 64 bits (.exe) :
Génère `windows/installer/Omega-Code-Studio-Setup-v2.0.0.exe` contenant :
- L'assistant d'installation graphique natif Win32 (Français, sans droits Admin requis)
- Le lanceur natif `OmegaCodeStudio.exe` et le désinstallateur `Uninstall-OmegaCodeStudio.exe`
- Le runtime complet Python 3.12 (win_amd64) + PyQt6 + SQLite3 + Omega Code Studio v2.0
"""

from __future__ import annotations

import io
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
import zlib
from pathlib import Path
from typing import List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
WIN_DIR = REPO_ROOT / "windows"
SRC_DIR = WIN_DIR / "src"
OUT_DIR = WIN_DIR / "installer"
WORK_DIR = Path("/tmp/win_build")

PYTHON_EMBED_URL = (
    "https://files.pythonhosted.org/packages/59/87/"
    "c9587bdcabe59533841345719562e4428b4e50cdaa113bbef4e19118150c/python_embed-3.12.0.tar.gz"
)
ZLIB_SRC_URL = "https://codeload.github.com/madler/zlib/tar.gz/refs/tags/v1.3.1"


def generate_multi_size_ico(ico_path: Path) -> None:
    """Génère une icône Windows multi-résolution (.ico : 16, 32, 48, 64, 256 px) haute netteté."""
    from PyQt6.QtCore import QBuffer, QIODevice, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen
    from PyQt6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    sizes = [16, 32, 48, 64, 256]
    png_blobs: List[Tuple[int, bytes]] = []

    for sz in sizes:
        img = QImage(sz, sz, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = float(sz)
        pad = max(1.0, s * 0.05)

        bg = QLinearGradient(0, 0, s, s)
        bg.setColorAt(0.0, QColor("#0f172a"))
        bg.setColorAt(0.55, QColor("#261447"))
        bg.setColorAt(1.0, QColor("#0e4f6e"))
        p.setBrush(bg)
        pen = QPen(QColor("#38bdf8"), max(1.2, s * 0.055))
        p.setPen(pen)
        p.drawRoundedRect(QRectF(pad, pad, s - 2 * pad, s - 2 * pad), s * 0.23, s * 0.23)

        f = QFont("Sans Serif", max(7, int(s * 0.48)), QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor("#f8fafc"))
        p.drawText(QRectF(0, -s * 0.03, s, s), Qt.AlignmentFlag.AlignCenter, "Ω")
        p.end()

        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        png_blobs.append((sz, bytes(buf.data())))

    # Assemblage de l'en-tête ICO standard (Vista+ PNG frames)
    header = struct.pack("<HHH", 0, 1, len(png_blobs))
    offset = 6 + 16 * len(png_blobs)
    entries = []
    payloads = []
    for sz, blob in png_blobs:
        w_byte = 0 if sz >= 256 else sz
        h_byte = 0 if sz >= 256 else sz
        entries.append(struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, len(blob), offset))
        payloads.append(blob)
        offset += len(blob)

    ico_path.parent.mkdir(parents=True, exist_ok=True)
    ico_path.write_bytes(header + b"".join(entries) + b"".join(payloads))
    print(f"[ICO] Icône Windows générée : {ico_path} ({ico_path.stat().st_size} octets)")


def ensure_build_inputs() -> Tuple[Path, Path, Path]:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    wheels_dir = WORK_DIR / "wheels"
    wheels_dir.mkdir(exist_ok=True)

    if not list(wheels_dir.glob("pyqt6_qt6-*win_amd64.whl")):
        print("[DL] Téléchargement des wheels Windows PyQt6 (win_amd64, cp312)...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "-q",
                "--dest",
                str(wheels_dir),
                "--platform",
                "win_amd64",
                "--python-version",
                "312",
                "--only-binary=:all:",
                "PyQt6",
            ]
        )

    py_dir = WORK_DIR / "py312_unpacked" / "cp312"
    if not (py_dir / "pythonw.exe").exists():
        print("[DL] Téléchargement du runtime officiel Python 3.12 Embeddable (win_amd64)...")
        tgz = WORK_DIR / "python_embed-3.12.0.tar.gz"
        if not tgz.exists():
            urllib.request.urlretrieve(PYTHON_EMBED_URL, tgz)
        unpack_tmp = WORK_DIR / "py312"
        unpack_tmp.mkdir(exist_ok=True)
        with tarfile.open(tgz, "r:gz") as tf:
            tf.extractall(unpack_tmp)
        data_zip = next(unpack_tmp.rglob("data.zip"))
        out_unp = WORK_DIR / "py312_unpacked"
        out_unp.mkdir(exist_ok=True)
        with zipfile.ZipFile(data_zip) as zf:
            zf.extractall(out_unp)

    zlib_dir = WORK_DIR / "zlib-1.3.1"
    if not (zlib_dir / "zlib.h").exists():
        print("[DL] Téléchargement des sources C zlib 1.3.1...")
        ztgz = WORK_DIR / "zlib.tar.gz"
        if not ztgz.exists():
            urllib.request.urlretrieve(ZLIB_SRC_URL, ztgz)
        with tarfile.open(ztgz, "r:gz") as tf:
            tf.extractall(WORK_DIR)

    return wheels_dir, py_dir, zlib_dir


def compile_win32_binaries(ico_path: Path, zlib_dir: Path) -> Tuple[Path, Path, Path]:
    bin_out = WORK_DIR / "compiled_exes"
    bin_out.mkdir(parents=True, exist_ok=True)

    # Copie l'icône et le manifeste à côté du fichier .rc pour des chemins relatifs simples
    shutil.copy2(ico_path, bin_out / "omega-code-studio.ico")
    shutil.copy2(SRC_DIR / "app.manifest", bin_out / "app.manifest")

    def make_rc(name: str, desc: str, orig_exe: str) -> Path:
        rc_file = bin_out / f"{name}.rc"
        res_file = bin_out / f"{name}.res"
        rc_file.write_text(
            f"""1 ICON "omega-code-studio.ico"
1 24 "app.manifest"

1 VERSIONINFO
FILEVERSION 2,0,0,0
PRODUCTVERSION 2,0,0,0
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040C04B0"
    BEGIN
      VALUE "CompanyName", "Omega Code Studio\\0"
      VALUE "FileDescription", "{desc}\\0"
      VALUE "FileVersion", "2.0.0.0\\0"
      VALUE "InternalName", "{name}\\0"
      VALUE "OriginalFilename", "{orig_exe}\\0"
      VALUE "ProductName", "Omega Code Studio\\0"
      VALUE "ProductVersion", "2.0.0\\0"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x040C, 1200
  END
END
""",
            encoding="utf-8",
        )
        subprocess.check_call([sys.executable, "-m", "ziglang", "rc", str(rc_file), str(res_file)], cwd=str(bin_out))
        return res_file

    print("[ZIG] Compilation des exécutables natifs Windows x86_64...")
    res_launcher = make_rc("launcher", "Omega Code Studio - IDE Algorithmique Moderne", "OmegaCodeStudio.exe")
    res_uninst = make_rc("uninstaller", "Désinstallateur Omega Code Studio", "Uninstall-OmegaCodeStudio.exe")
    res_setup = make_rc("setup", "Assistant d'installation Omega Code Studio v2.0", "Omega-Code-Studio-Setup-v2.0.0.exe")

    common_flags = [
        sys.executable,
        "-m",
        "ziglang",
        "cc",
        "-target",
        "x86_64-windows-gnu",
        "-std=c11",
        "-Os",
        "-s",
        "-municode",
        "-Wl,--subsystem,windows",
    ]

    launcher_exe = bin_out / "OmegaCodeStudio.exe"
    subprocess.check_call(
        common_flags
        + [
            str(SRC_DIR / "launcher.c"),
            str(res_launcher),
            "-lshell32",
            "-luser32",
            "-o",
            str(launcher_exe),
        ]
    )

    uninst_exe = bin_out / "Uninstall-OmegaCodeStudio.exe"
    subprocess.check_call(
        common_flags
        + [
            str(SRC_DIR / "uninstaller.c"),
            str(res_uninst),
            "-lshell32",
            "-lole32",
            "-ladvapi32",
            "-luser32",
            "-o",
            str(uninst_exe),
        ]
    )

    zlib_c_files = [
        str(zlib_dir / fn)
        for fn in ("inflate.c", "inftrees.c", "inffast.c", "adler32.c", "crc32.c", "zutil.c")
    ]
    setup_stub_exe = bin_out / "setup_stub.exe"
    subprocess.check_call(
        common_flags
        + [
            f"-I{zlib_dir}",
            str(SRC_DIR / "setup_wizard.c"),
            *zlib_c_files,
            str(res_setup),
            "-lcomctl32",
            "-lshell32",
            "-lole32",
            "-luuid",
            "-ladvapi32",
            "-lgdi32",
            "-luser32",
            "-o",
            str(setup_stub_exe),
        ]
    )

    return launcher_exe, uninst_exe, setup_stub_exe


def stage_windows_bundle(
    wheels_dir: Path,
    py_dir: Path,
    ico_path: Path,
    launcher_exe: Path,
    uninst_exe: Path,
) -> Path:
    stage = WORK_DIR / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # 1. Exécutables principaux
    shutil.copy2(launcher_exe, stage / "OmegaCodeStudio.exe")
    shutil.copy2(uninst_exe, stage / "Uninstall-OmegaCodeStudio.exe")

    # 2. Code source d'Omega Code Studio, exemples et ressources
    shutil.copytree(
        REPO_ROOT / "omega_studio",
        stage / "omega_studio",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(REPO_ROOT / "examples", stage / "examples")
    (stage / "assets").mkdir(exist_ok=True)
    shutil.copy2(ico_path, stage / "assets" / "omega-code-studio.ico")
    shutil.copy2(REPO_ROOT / "assets" / "omega-studio-code.svg", stage / "assets" / "omega-studio-code.svg")
    shutil.copy2(REPO_ROOT / "README.md", stage / "README.md")

    # 3. Runtime Python 3.12 Windows x64
    rt = stage / "runtime"
    shutil.copytree(py_dir, rt)
    # Configuration déterministe des chemins de recherche Python embarqué
    (rt / "python312._pth").write_text(
        "python312.zip\r\n.\r\n..\r\nLib\\site-packages\r\nimport site\r\n",
        encoding="utf-8",
    )

    site_pkg = rt / "Lib" / "site-packages"
    site_pkg.mkdir(parents=True, exist_ok=True)

    # 4. Extraction sélective optimale de PyQt6 + PyQt6-sip + Qt6 DLLs/Plugins
    whl_sip = next(wheels_dir.glob("pyqt6_sip-*win_amd64.whl"))
    whl_pyqt = next(wheels_dir.glob("pyqt6-6.*win_amd64.whl"))
    whl_qt6 = next(wheels_dir.glob("pyqt6_qt6-*win_amd64.whl"))

    with zipfile.ZipFile(whl_sip) as zf:
        for name in zf.namelist():
            if name.startswith("PyQt6/"):
                zf.extract(name, site_pkg)

    keep_pyds = {
        "PyQt6/__init__.py",
        "PyQt6/QtCore.pyd",
        "PyQt6/QtGui.pyd",
        "PyQt6/QtWidgets.pyd",
        "PyQt6/QtSvg.pyd",
        "PyQt6/QtSvgWidgets.pyd",
        "PyQt6/QtPrintSupport.pyd",
    }
    with zipfile.ZipFile(whl_pyqt) as zf:
        for name in zf.namelist():
            if name in keep_pyds:
                zf.extract(name, site_pkg)

    keep_qt_bins = {
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6Svg.dll",
        "Qt6SvgWidgets.dll",
        "Qt6PrintSupport.dll",
        "concrt140.dll",
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "msvcp140_atomic_wait.dll",
        "msvcp140_codecvt_ids.dll",
        "vccorlib140.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "vcruntime140_threads.dll",
    }
    keep_plugin_prefixes = (
        "PyQt6/Qt6/plugins/platforms/",
        "PyQt6/Qt6/plugins/styles/",
        "PyQt6/Qt6/plugins/iconengines/",
        "PyQt6/Qt6/plugins/imageformats/",
    )
    keep_translations = {
        "PyQt6/Qt6/translations/qtbase_fr.qm",
        "PyQt6/Qt6/translations/qt_fr.qm",
    }

    with zipfile.ZipFile(whl_qt6) as zf:
        for name in zf.namelist():
            fname = name.split("/")[-1]
            if name.startswith("PyQt6/Qt6/bin/") and fname in keep_qt_bins:
                zf.extract(name, site_pkg)
            elif name.startswith(keep_plugin_prefixes):
                zf.extract(name, site_pkg)
            elif name in keep_translations:
                zf.extract(name, site_pkg)

    verify_pe_dependencies(stage)
    return stage


def _pe_imports(raw: bytes) -> List[str]:
    if len(raw) < 0x100 or raw[:2] != b"MZ":
        return []
    pe_off = struct.unpack_from("<I", raw, 0x3C)[0]
    if pe_off + 24 >= len(raw) or raw[pe_off : pe_off + 4] != b"PE\x00\x00":
        return []
    num_sec = struct.unpack_from("<H", raw, pe_off + 6)[0]
    opt_sz = struct.unpack_from("<H", raw, pe_off + 20)[0]
    opt_off = pe_off + 24
    magic = struct.unpack_from("<H", raw, opt_off)[0]
    dd_off = opt_off + (112 if magic == 0x20B else 96)
    imp_rva, _ = struct.unpack_from("<II", raw, dd_off + 8)
    if imp_rva == 0:
        return []
    sec_off = opt_off + opt_sz
    secs = []
    for i in range(num_sec):
        s = sec_off + i * 40
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", raw, s + 8)
        secs.append((va, max(vsz, rsz), ptr))

    def rva2off(rva: int):
        for va, sz, ptr in secs:
            if va <= rva < va + sz:
                return ptr + (rva - va)
        return None

    pos = rva2off(imp_rva)
    res = []
    while pos is not None and pos + 20 <= len(raw):
        ilt, _, _, name_rva, _ = struct.unpack_from("<IIIII", raw, pos)
        if ilt == 0 and name_rva == 0:
            break
        noff = rva2off(name_rva)
        if noff is not None:
            end = raw.find(b"\x00", noff)
            res.append(raw[noff:end].decode("ascii", "replace"))
        pos += 20
    return res


def verify_pe_dependencies(stage: Path) -> None:
    """Vérifie statiquement que toutes les DLL non-système requises sont présentes dans le bundle."""
    bundled_dlls: Set[str] = {
        p.name.lower() for p in stage.rglob("*") if p.suffix.lower() in (".dll", ".pyd", ".exe")
    }
    win_system_dlls = {
        "kernel32.dll",
        "user32.dll",
        "gdi32.dll",
        "shell32.dll",
        "ole32.dll",
        "oleaut32.dll",
        "advapi32.dll",
        "shlwapi.dll",
        "ws2_32.dll",
        "winmm.dll",
        "dwmapi.dll",
        "uxtheme.dll",
        "imm32.dll",
        "wtsapi32.dll",
        "d3d9.dll",
        "d3d11.dll",
        "d3d12.dll",
        "dxgi.dll",
        "dwrite.dll",
        "d2d1.dll",
        "comdlg32.dll",
        "comctl32.dll",
        "netapi32.dll",
        "userenv.dll",
        "version.dll",
        "authz.dll",
        "mpr.dll",
        "synchronization.dll",
        "setupapi.dll",
        "cfgmgr32.dll",
        "propsys.dll",
        "shcore.dll",
        "uiautomationcore.dll",
        "mscms.dll",
        "ntdll.dll",
        "icuuc.dll",
        "icuin.dll",
        "msvcrt.dll",
        "ucrtbase.dll",
        "bcrypt.dll",
        "crypt32.dll",
        "iphlpapi.dll",
        "rpcrt4.dll",
        "pathcch.dll",
        "winspool.drv",
        "msi.dll",
        "powrprof.dll",
        "secur32.dll",
        "ncrypt.dll",
        "cabinet.dll",
    }

    missing: Set[Tuple[str, str]] = set()
    checked = 0
    for pe_file in stage.rglob("*"):
        if pe_file.suffix.lower() not in (".exe", ".dll", ".pyd"):
            continue
        checked += 1
        for dep in _pe_imports(pe_file.read_bytes()):
            dl = dep.lower()
            if dl.startswith("api-ms-win-") or dl in win_system_dlls or dl in bundled_dlls:
                continue
            missing.add((pe_file.name, dep))

    if missing:
        raise RuntimeError(f"DLL manquantes dans le bundle Windows : {sorted(missing)}")
    print(f"[CHECK] {checked} binaires PE32+ x86_64 vérifiés — 0 DLL manquante !")


def build_sfx_installer(stage: Path, setup_stub_exe: Path, output_exe: Path) -> None:
    files = sorted([p for p in stage.rglob("*") if p.is_file()])
    print(f"[PACK] Compression solide zlib de {len(files)} fichiers...")

    stream = io.BytesIO()
    stream.write(struct.pack("<I", len(files)))
    for fpath in files:
        rel = fpath.relative_to(stage).as_posix().encode("utf-8")
        raw = fpath.read_bytes()
        stream.write(struct.pack("<H", len(rel)))
        stream.write(rel)
        stream.write(struct.pack("<I", len(raw)))
        stream.write(raw)

    uncompressed_bytes = stream.getvalue()
    compressed_bytes = zlib.compress(uncompressed_bytes, level=9)

    # Test d'intégrité de décompression immédiat
    check_decomp = zlib.decompress(compressed_bytes)
    assert len(check_decomp) == len(uncompressed_bytes), "Échec de vérification zlib !"

    stub_bytes = setup_stub_exe.read_bytes()
    payload_offset = len(stub_bytes)
    footer = struct.pack(
        "<QQQ8s",
        payload_offset,
        len(compressed_bytes),
        len(uncompressed_bytes),
        b"OMG20WIN",
    )

    output_exe.parent.mkdir(parents=True, exist_ok=True)
    with open(output_exe, "wb") as f:
        f.write(stub_bytes)
        f.write(compressed_bytes)
        f.write(footer)

    mb_uncomp = len(uncompressed_bytes) / (1024 * 1024)
    mb_final = output_exe.stat().st_size / (1024 * 1024)
    print(
        f"[OK] Installateur Windows créé : {output_exe}\n"
        f"     Taille non compressée : {mb_uncomp:.1f} Mo -> Installateur .exe autonome : {mb_final:.1f} Mo"
    )


def main() -> None:
    ico_path = REPO_ROOT / "assets" / "omega-code-studio.ico"
    generate_multi_size_ico(ico_path)
    wheels_dir, py_dir, zlib_dir = ensure_build_inputs()
    launcher_exe, uninst_exe, setup_stub_exe = compile_win32_binaries(ico_path, zlib_dir)
    stage = stage_windows_bundle(wheels_dir, py_dir, ico_path, launcher_exe, uninst_exe)
    out_exe = OUT_DIR / "Omega-Code-Studio-Setup-v2.0.0.exe"
    build_sfx_installer(stage, setup_stub_exe, out_exe)


if __name__ == "__main__":
    main()
