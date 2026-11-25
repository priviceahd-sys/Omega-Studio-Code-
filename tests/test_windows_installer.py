from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SETUP_EXE = REPO_ROOT / "windows" / "installer" / "Omega-Code-Studio-Setup-v2.0.0.exe"


def _check_pe32_plus_gui(raw: bytes) -> None:
    assert raw[:2] == b"MZ", "En-tête DOS MZ manquant"
    pe_off = struct.unpack_from("<I", raw, 0x3C)[0]
    assert raw[pe_off : pe_off + 4] == b"PE\x00\x00", "Signature PE manquante"
    machine = struct.unpack_from("<H", raw, pe_off + 4)[0]
    assert machine == 0x8664, f"Architecture attendue x86_64 (0x8664), reçu {hex(machine)}"
    opt_off = pe_off + 24
    magic = struct.unpack_from("<H", raw, opt_off)[0]
    assert magic == 0x20B, "Attendu un exécutable 64 bits PE32+"
    subsystem = struct.unpack_from("<H", raw, opt_off + 68)[0]
    assert subsystem == 2, f"Attendu IMAGE_SUBSYSTEM_WINDOWS_GUI (2), reçu {subsystem}"


@pytest.mark.skipif(not SETUP_EXE.exists(), reason="Installateur Windows non généré dans cet environnement")
def test_windows_installer_pe_and_payload() -> None:
    data = SETUP_EXE.read_bytes()
    _check_pe32_plus_gui(data)

    # Vérifie le pied d'archive OMG20WIN et le manifeste UAC asInvoker + PerMonitorV2 intégré au stub Win32
    payload_offset, comp_size, uncomp_size, magic = struct.unpack_from("<QQQ8s", data, len(data) - 32)
    assert magic == b"OMG20WIN"
    assert payload_offset + comp_size + 32 == len(data)
    assert b"asInvoker" in data[:payload_offset]
    assert b"PerMonitorV2" in data[:payload_offset]

    raw_stream = zlib.decompress(data[payload_offset : payload_offset + comp_size])
    assert len(raw_stream) == uncomp_size

    pos = 0
    (file_count,) = struct.unpack_from("<I", raw_stream, pos)
    pos += 4
    assert file_count >= 100

    extracted_entries = {}
    for _ in range(file_count):
        (plen,) = struct.unpack_from("<H", raw_stream, pos)
        pos += 2
        rel_path = raw_stream[pos : pos + plen].decode("utf-8")
        pos += plen
        (fsize,) = struct.unpack_from("<I", raw_stream, pos)
        pos += 4
        extracted_entries[rel_path] = raw_stream[pos : pos + fsize]
        pos += fsize

    assert pos == len(raw_stream)

    required_files = [
        "OmegaCodeStudio.exe",
        "Uninstall-OmegaCodeStudio.exe",
        "assets/omega-code-studio.ico",
        "assets/omega-studio-code.svg",
        "runtime/pythonw.exe",
        "runtime/python312.dll",
        "runtime/python312.zip",
        "runtime/python312._pth",
        "runtime/sqlite3.dll",
        "runtime/_sqlite3.pyd",
        "runtime/Lib/site-packages/PyQt6/__init__.py",
        "runtime/Lib/site-packages/PyQt6/QtCore.pyd",
        "runtime/Lib/site-packages/PyQt6/QtGui.pyd",
        "runtime/Lib/site-packages/PyQt6/QtWidgets.pyd",
        "runtime/Lib/site-packages/PyQt6/QtSvg.pyd",
        "runtime/Lib/site-packages/PyQt6/Qt6/bin/Qt6Core.dll",
        "runtime/Lib/site-packages/PyQt6/Qt6/bin/Qt6Gui.dll",
        "runtime/Lib/site-packages/PyQt6/Qt6/bin/Qt6Widgets.dll",
        "runtime/Lib/site-packages/PyQt6/Qt6/plugins/platforms/qwindows.dll",
        "runtime/Lib/site-packages/PyQt6/Qt6/plugins/styles/qmodernwindowsstyle.dll",
        "omega_studio/app.py",
        "omega_studio/ui/main_window.py",
        "omega_studio/ui/appearance_studio.py",
        "omega_studio/resources/alg32_help.json",
        "examples/01_bienvenue_omega.alg",
    ]
    for req in required_files:
        assert req in extracted_entries, f"Fichier requis absent de l'installateur : {req}"

    _check_pe32_plus_gui(extracted_entries["OmegaCodeStudio.exe"])
    _check_pe32_plus_gui(extracted_entries["Uninstall-OmegaCodeStudio.exe"])

    pth_lines = extracted_entries["runtime/python312._pth"].decode("utf-8").splitlines()
    assert ".." in pth_lines
    assert "Lib\\site-packages" in pth_lines
