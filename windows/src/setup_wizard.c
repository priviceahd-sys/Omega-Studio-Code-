/*
 * Omega-Code-Studio-Setup-v2.0.0.exe
 * Assistant d'installation graphique natif Windows 10 / 11 (x86_64)
 * Autonome (inclut Python 3.12 + PyQt6 + SQLite3 + Omega Code Studio v2.0)
 * Ne nécessite aucun droit Administrateur (installe dans %LOCALAPPDATA%\Programs\OmegaCodeStudio).
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define COBJMACROS
#include <windows.h>
#include <commctrl.h>
#include <shlobj.h>
#include <objbase.h>
#include <shobjidl.h>
#include <shellapi.h>
#include <stdint.h>
#include <wchar.h>
#include "zlib.h"

#define ID_EDIT_DIR      101
#define ID_BTN_BROWSE    102
#define ID_CHK_DESKTOP   103
#define ID_CHK_STARTMENU 104
#define ID_CHK_ASSOC     105
#define ID_CHK_LAUNCH    106
#define ID_PROGRESS      107
#define ID_BTN_INSTALL   108
#define ID_BTN_CANCEL    109
#define ID_LBL_STATUS    110

#define WM_APP_PROGRESS  (WM_APP + 1)
#define WM_APP_DONE      (WM_APP + 2)

#pragma pack(push, 1)
typedef struct {
    uint64_t payload_offset;
    uint64_t compressed_size;
    uint64_t uncompressed_size;
    char     magic[8];
} SfxFooter;
#pragma pack(pop)

typedef struct {
    HANDLE   hFile;
    uint64_t comp_remaining;
    z_stream zs;
    uint8_t  in_buf[65536];
    int      z_eof;
} ZStreamReader;

static HWND g_hwnd = NULL;
static HWND g_editDir = NULL;
static HWND g_btnBrowse = NULL;
static HWND g_chkDesktop = NULL;
static HWND g_chkStartMenu = NULL;
static HWND g_chkAssoc = NULL;
static HWND g_chkLaunch = NULL;
static HWND g_progress = NULL;
static HWND g_lblStatus = NULL;
static HWND g_btnInstall = NULL;
static HWND g_btnCancel = NULL;
static HFONT g_fontTitle = NULL;
static HFONT g_fontSub = NULL;
static HFONT g_fontUI = NULL;
static HBRUSH g_bgBrush = NULL;

static volatile LONG g_installing = 0;
static volatile LONG g_cancelReq = 0;
static wchar_t g_statusText[512] = L"Prêt à installer Omega Code Studio v2.0 sur cet ordinateur.";
static wchar_t g_errorText[512] = L"";

typedef struct {
    wchar_t installDir[MAX_PATH * 2];
    BOOL    makeDesktop;
    BOOL    makeStartMenu;
    BOOL    assocAlg;
    BOOL    launchAfter;
    BOOL    silentMode;
} InstallOptions;

static InstallOptions g_opts;

/* =========================================================
 * Utilitaires de décompression flux zlib
 * ========================================================= */

static int zreader_init(ZStreamReader *r, HANDLE hFile, uint64_t offset, uint64_t comp_size) {
    ZeroMemory(r, sizeof(*r));
    r->hFile = hFile;
    r->comp_remaining = comp_size;

    LARGE_INTEGER li;
    li.QuadPart = (LONGLONG)offset;
    if (!SetFilePointerEx(hFile, li, NULL, FILE_BEGIN)) {
        return 0;
    }
    if (inflateInit(&r->zs) != Z_OK) {
        return 0;
    }
    return 1;
}

static void zreader_close(ZStreamReader *r) {
    inflateEnd(&r->zs);
}

static int zreader_read_exact(ZStreamReader *r, void *out_ptr, uint32_t count) {
    uint8_t *dst = (uint8_t *)out_ptr;
    uint32_t got = 0;

    while (got < count) {
        if (r->zs.avail_in == 0 && r->comp_remaining > 0) {
            DWORD to_read = (r->comp_remaining > sizeof(r->in_buf))
                                ? (DWORD)sizeof(r->in_buf)
                                : (DWORD)r->comp_remaining;
            DWORD bytes_read = 0;
            if (!ReadFile(r->hFile, r->in_buf, to_read, &bytes_read, NULL) || bytes_read == 0) {
                return 0;
            }
            r->comp_remaining -= bytes_read;
            r->zs.next_in = r->in_buf;
            r->zs.avail_in = bytes_read;
        }

        r->zs.next_out = dst + got;
        r->zs.avail_out = count - got;

        int ret = inflate(&r->zs, Z_NO_FLUSH);
        uint32_t produced = (count - got) - r->zs.avail_out;
        got += produced;

        if (ret == Z_STREAM_END) {
            r->z_eof = 1;
            if (got < count) return 0;
            break;
        }
        if (ret != Z_OK) {
            return 0;
        }
    }
    return 1;
}

/* =========================================================
 * Système de fichiers, raccourcis .lnk et Registre Windows
 * ========================================================= */

static void ensure_dir_tree(const wchar_t *dirPath) {
    wchar_t tmp[MAX_PATH * 2];
    wcscpy(tmp, dirPath);
    for (wchar_t *p = tmp; *p; ++p) {
        if (*p == L'/') *p = L'\\';
    }
    size_t len = wcslen(tmp);
    if (len > 0 && tmp[len - 1] == L'\\') {
        tmp[len - 1] = L'\0';
    }
    for (wchar_t *p = tmp + 3; *p; ++p) {
        if (*p == L'\\') {
            *p = L'\0';
            CreateDirectoryW(tmp, NULL);
            *p = L'\\';
        }
    }
    CreateDirectoryW(tmp, NULL);
}

static void ensure_parent_dir(const wchar_t *filePath) {
    wchar_t dir[MAX_PATH * 2];
    wcscpy(dir, filePath);
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash) {
        *slash = L'\0';
        ensure_dir_tree(dir);
    }
}

static void create_shell_shortcut(
    const wchar_t *lnkPath,
    const wchar_t *targetExe,
    const wchar_t *workDir,
    const wchar_t *iconPath,
    const wchar_t *desc
) {
    IShellLinkW *psl = NULL;
    HRESULT hr = CoCreateInstance(
        &CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER, &IID_IShellLinkW, (void **)&psl
    );
    if (SUCCEEDED(hr) && psl) {
        IShellLinkW_SetPath(psl, targetExe);
        IShellLinkW_SetWorkingDirectory(psl, workDir);
        IShellLinkW_SetIconLocation(psl, iconPath, 0);
        IShellLinkW_SetDescription(psl, desc);

        IPersistFile *ppf = NULL;
        if (SUCCEEDED(IShellLinkW_QueryInterface(psl, &IID_IPersistFile, (void **)&ppf)) && ppf) {
            ensure_parent_dir(lnkPath);
            IPersistFile_Save(ppf, lnkPath, TRUE);
            IPersistFile_Release(ppf);
        }
        IShellLinkW_Release(psl);
    }
}

static void reg_write_str(HKEY root, const wchar_t *subkey, const wchar_t *name, const wchar_t *val) {
    HKEY hk = NULL;
    if (RegCreateKeyExW(root, subkey, 0, NULL, 0, KEY_WRITE, NULL, &hk, NULL) == ERROR_SUCCESS) {
        DWORD bytes = (DWORD)((wcslen(val) + 1) * sizeof(wchar_t));
        RegSetValueExW(hk, name, 0, REG_SZ, (const BYTE *)val, bytes);
        RegCloseKey(hk);
    }
}

static void reg_write_dword(HKEY root, const wchar_t *subkey, const wchar_t *name, DWORD val) {
    HKEY hk = NULL;
    if (RegCreateKeyExW(root, subkey, 0, NULL, 0, KEY_WRITE, NULL, &hk, NULL) == ERROR_SUCCESS) {
        RegSetValueExW(hk, name, 0, REG_DWORD, (const BYTE *)&val, sizeof(DWORD));
        RegCloseKey(hk);
    }
}

/* =========================================================
 * Thread d'extraction & configuration Windows
 * ========================================================= */

static DWORD WINAPI install_worker_thread(LPVOID param) {
    (void)param;
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    wchar_t selfPath[MAX_PATH * 2];
    GetModuleFileNameW(NULL, selfPath, MAX_PATH * 2);

    HANDLE hSelf = CreateFileW(
        selfPath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL
    );
    if (hSelf == INVALID_HANDLE_VALUE) {
        wcscpy(g_errorText, L"Impossible d'ouvrir le fichier d'installation.");
        CoUninitialize();
        if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
        return 1;
    }

    LARGE_INTEGER fileSize;
    if (!GetFileSizeEx(hSelf, &fileSize) || fileSize.QuadPart < (LONGLONG)sizeof(SfxFooter)) {
        CloseHandle(hSelf);
        wcscpy(g_errorText, L"Archive d'installation invalide ou tronquée.");
        CoUninitialize();
        if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
        return 1;
    }

    LARGE_INTEGER footerPos;
    footerPos.QuadPart = fileSize.QuadPart - (LONGLONG)sizeof(SfxFooter);
    SetFilePointerEx(hSelf, footerPos, NULL, FILE_BEGIN);

    SfxFooter footer;
    DWORD br = 0;
    if (!ReadFile(hSelf, &footer, sizeof(footer), &br, NULL) || br != sizeof(footer) ||
        memcmp(footer.magic, "OMG20WIN", 8) != 0) {
        CloseHandle(hSelf);
        wcscpy(g_errorText, L"Signature de l'archive Omega Code Studio introuvable (OMG20WIN).");
        CoUninitialize();
        if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
        return 1;
    }

    ensure_dir_tree(g_opts.installDir);

    ZStreamReader zr;
    if (!zreader_init(&zr, hSelf, footer.payload_offset, footer.compressed_size)) {
        CloseHandle(hSelf);
        wcscpy(g_errorText, L"Impossible d'initialiser le décompresseur zlib.");
        CoUninitialize();
        if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
        return 1;
    }

    uint32_t fileCount = 0;
    if (!zreader_read_exact(&zr, &fileCount, sizeof(fileCount))) {
        zreader_close(&zr);
        CloseHandle(hSelf);
        wcscpy(g_errorText, L"Erreur de lecture de l'en-tête d'archive.");
        CoUninitialize();
        if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
        return 1;
    }

    static uint8_t copyBuf[65536];
    uint64_t bytesDone = 0;
    int lastPct = -1;

    for (uint32_t i = 0; i < fileCount; ++i) {
        if (g_cancelReq) {
            zreader_close(&zr);
            CloseHandle(hSelf);
            wcscpy(g_errorText, L"Installation annulée par l'utilisateur.");
            CoUninitialize();
            if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
            return 2;
        }

        uint16_t pathLen = 0;
        if (!zreader_read_exact(&zr, &pathLen, sizeof(pathLen)) || pathLen == 0 || pathLen >= 1024) {
            zreader_close(&zr);
            CloseHandle(hSelf);
            wcscpy(g_errorText, L"Chemin de fichier corrompu dans l'archive.");
            CoUninitialize();
            if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
            return 1;
        }

        char relUtf8[1024];
        if (!zreader_read_exact(&zr, relUtf8, pathLen)) {
            zreader_close(&zr);
            CloseHandle(hSelf);
            wcscpy(g_errorText, L"Fin inattendue de l'archive.");
            CoUninitialize();
            if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
            return 1;
        }
        relUtf8[pathLen] = '\0';

        uint32_t rawSize = 0;
        if (!zreader_read_exact(&zr, &rawSize, sizeof(rawSize))) {
            zreader_close(&zr);
            CloseHandle(hSelf);
            wcscpy(g_errorText, L"Taille de fichier invalide dans l'archive.");
            CoUninitialize();
            if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
            return 1;
        }

        wchar_t relW[1024];
        MultiByteToWideChar(CP_UTF8, 0, relUtf8, -1, relW, 1024);
        for (wchar_t *p = relW; *p; ++p) {
            if (*p == L'/') *p = L'\\';
        }

        wchar_t outPath[MAX_PATH * 2];
        wsprintfW(outPath, L"%s\\%s", g_opts.installDir, relW);
        ensure_parent_dir(outPath);

        SetFileAttributesW(outPath, FILE_ATTRIBUTE_NORMAL);
        HANDLE hOut = CreateFileW(
            outPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL
        );
        if (hOut == INVALID_HANDLE_VALUE) {
            zreader_close(&zr);
            CloseHandle(hSelf);
            wsprintfW(
                g_errorText,
                L"Impossible d'écrire le fichier :\n%s\n(Fermez Omega Code Studio s'il est ouvert.)",
                outPath
            );
            CoUninitialize();
            if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
            return 1;
        }

        uint32_t rem = rawSize;
        while (rem > 0) {
            uint32_t chunk = (rem > sizeof(copyBuf)) ? (uint32_t)sizeof(copyBuf) : rem;
            if (!zreader_read_exact(&zr, copyBuf, chunk)) {
                CloseHandle(hOut);
                zreader_close(&zr);
                CloseHandle(hSelf);
                wcscpy(g_errorText, L"Erreur pendant la décompression des fichiers.");
                CoUninitialize();
                if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
                return 1;
            }
            DWORD bw = 0;
            if (!WriteFile(hOut, copyBuf, chunk, &bw, NULL) || bw != chunk) {
                CloseHandle(hOut);
                zreader_close(&zr);
                CloseHandle(hSelf);
                wcscpy(g_errorText, L"Espace disque insuffisant ou erreur d'écriture.");
                CoUninitialize();
                if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 0, 0);
                return 1;
            }
            rem -= chunk;
            bytesDone += chunk;

            int pct = (footer.uncompressed_size > 0)
                          ? (int)((bytesDone * 95ULL) / footer.uncompressed_size)
                          : (int)((i * 95U) / (fileCount ? fileCount : 1));
            if (pct != lastPct) {
                lastPct = pct;
                const wchar_t *shortName = wcsrchr(relW, L'\\');
                shortName = shortName ? (shortName + 1) : relW;
                wsprintfW(g_statusText, L"Installation (%d%%) — %s", pct, shortName);
                if (g_hwnd) PostMessageW(g_hwnd, WM_APP_PROGRESS, (WPARAM)pct, 0);
            }
        }
        CloseHandle(hOut);
    }

    zreader_close(&zr);
    CloseHandle(hSelf);

    /* Création des raccourcis et clés de Registre */
    wsprintfW(g_statusText, L"Configuration des raccourcis Windows (98%%)...");
    if (g_hwnd) PostMessageW(g_hwnd, WM_APP_PROGRESS, 98, 0);

    wchar_t mainExe[MAX_PATH * 2];
    wchar_t uninstExe[MAX_PATH * 2];
    wchar_t iconIco[MAX_PATH * 2];
    wsprintfW(mainExe, L"%s\\OmegaCodeStudio.exe", g_opts.installDir);
    wsprintfW(uninstExe, L"%s\\Uninstall-OmegaCodeStudio.exe", g_opts.installDir);
    wsprintfW(iconIco, L"%s\\assets\\omega-code-studio.ico", g_opts.installDir);

    if (g_opts.makeDesktop) {
        wchar_t desktopDir[MAX_PATH];
        if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_DESKTOPDIRECTORY, NULL, 0, desktopDir))) {
            wchar_t lnk[MAX_PATH * 2];
            wsprintfW(lnk, L"%s\\Omega Code Studio.lnk", desktopDir);
            create_shell_shortcut(
                lnk,
                mainExe,
                g_opts.installDir,
                iconIco,
                L"Omega Code Studio v2.0 — IDE Algorithmique Moderne (Alg_32)"
            );
        }
    }

    if (g_opts.makeStartMenu) {
        wchar_t programsDir[MAX_PATH];
        if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAMS, NULL, 0, programsDir))) {
            wchar_t lnkApp[MAX_PATH * 2];
            wchar_t lnkUninst[MAX_PATH * 2];
            wsprintfW(lnkApp, L"%s\\Omega Code Studio\\Omega Code Studio.lnk", programsDir);
            wsprintfW(lnkUninst, L"%s\\Omega Code Studio\\Désinstaller Omega Code Studio.lnk", programsDir);
            create_shell_shortcut(
                lnkApp,
                mainExe,
                g_opts.installDir,
                iconIco,
                L"Omega Code Studio v2.0 — IDE Algorithmique Moderne (Alg_32)"
            );
            create_shell_shortcut(
                lnkUninst,
                uninstExe,
                g_opts.installDir,
                uninstExe,
                L"Désinstaller Omega Code Studio"
            );
        }
    }

    if (g_opts.assocAlg) {
        wchar_t openCmd[MAX_PATH * 3];
        wchar_t defIcon[MAX_PATH * 2];
        wsprintfW(openCmd, L"\"%s\" \"%%1\"", mainExe);
        wsprintfW(defIcon, L"\"%s\",0", iconIco);

        reg_write_str(HKEY_CURRENT_USER, L"Software\\Classes\\.alg", NULL, L"OmegaCodeStudio.alg");
        reg_write_str(
            HKEY_CURRENT_USER,
            L"Software\\Classes\\OmegaCodeStudio.alg",
            NULL,
            L"Algorithme Alg_32 / Omega Code Studio"
        );
        reg_write_str(
            HKEY_CURRENT_USER,
            L"Software\\Classes\\OmegaCodeStudio.alg\\DefaultIcon",
            NULL,
            defIcon
        );
        reg_write_str(
            HKEY_CURRENT_USER,
            L"Software\\Classes\\OmegaCodeStudio.alg\\shell\\open\\command",
            NULL,
            openCmd
        );
        SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    }

    /* Enregistrement dans Applications installées (Ajout/Suppression de programmes Windows) */
    const wchar_t *uninstKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OmegaCodeStudio";
    wchar_t uninstCmd[MAX_PATH * 2];
    wsprintfW(uninstCmd, L"\"%s\"", uninstExe);
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"DisplayName", L"Omega Code Studio v2.0");
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"DisplayVersion", L"2.0.0");
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"Publisher", L"Omega Code Studio");
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"DisplayIcon", mainExe);
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"InstallLocation", g_opts.installDir);
    reg_write_str(HKEY_CURRENT_USER, uninstKey, L"UninstallString", uninstCmd);
    reg_write_dword(HKEY_CURRENT_USER, uninstKey, L"NoModify", 1);
    reg_write_dword(HKEY_CURRENT_USER, uninstKey, L"NoRepair", 1);

    wsprintfW(g_statusText, L"Installation terminée avec succès (100%%) !");
    if (g_hwnd) PostMessageW(g_hwnd, WM_APP_PROGRESS, 100, 0);

    CoUninitialize();
    if (g_hwnd) PostMessageW(g_hwnd, WM_APP_DONE, 1, 0);
    return 0;
}

/* =========================================================
 * Interface graphique de l'assistant Setup Windows
 * ========================================================= */

static void browse_for_folder(HWND hwnd) {
    BROWSEINFOW bi;
    ZeroMemory(&bi, sizeof(bi));
    bi.hwndOwner = hwnd;
    bi.lpszTitle = L"Choisissez le dossier d'installation d'Omega Code Studio :";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE pidl = SHBrowseForFolderW(&bi);
    if (pidl) {
        wchar_t selected[MAX_PATH];
        if (SHGetPathFromIDListW(pidl, selected)) {
            wchar_t full[MAX_PATH * 2];
            wsprintfW(full, L"%s\\OmegaCodeStudio", selected);
            SetWindowTextW(g_editDir, full);
        }
        CoTaskMemFree(pidl);
    }
}

static void start_installation(HWND hwnd) {
    if (InterlockedCompareExchange(&g_installing, 1, 0) != 0) {
        return;
    }
    g_cancelReq = 0;
    GetWindowTextW(g_editDir, g_opts.installDir, MAX_PATH * 2);
    if (wcslen(g_opts.installDir) < 3) {
        InterlockedExchange(&g_installing, 0);
        MessageBoxW(hwnd, L"Veuillez indiquer un dossier d'installation valide.", L"Omega Code Studio", MB_OK | MB_ICONWARNING);
        return;
    }

    g_opts.makeDesktop = (SendMessageW(g_chkDesktop, BM_GETCHECK, 0, 0) == BST_CHECKED);
    g_opts.makeStartMenu = (SendMessageW(g_chkStartMenu, BM_GETCHECK, 0, 0) == BST_CHECKED);
    g_opts.assocAlg = (SendMessageW(g_chkAssoc, BM_GETCHECK, 0, 0) == BST_CHECKED);
    g_opts.launchAfter = (SendMessageW(g_chkLaunch, BM_GETCHECK, 0, 0) == BST_CHECKED);

    EnableWindow(g_editDir, FALSE);
    EnableWindow(g_btnBrowse, FALSE);
    EnableWindow(g_chkDesktop, FALSE);
    EnableWindow(g_chkStartMenu, FALSE);
    EnableWindow(g_chkAssoc, FALSE);
    EnableWindow(g_chkLaunch, FALSE);
    EnableWindow(g_btnInstall, FALSE);

    HANDLE hThread = CreateThread(NULL, 0, install_worker_thread, NULL, 0, NULL);
    if (hThread) {
        CloseHandle(hThread);
    }
}

static void paint_header_banner(HDC hdc, RECT rcClient) {
    RECT rcBanner = {0, 0, rcClient.right, 86};

    /* Dégradé horizontal Aurore Boréale (#0F172A -> #311B58 -> #0E7490) */
    int steps = 120;
    int w = rcBanner.right - rcBanner.left;
    for (int i = 0; i < steps; ++i) {
        int x0 = (i * w) / steps;
        int x1 = ((i + 1) * w) / steps;
        double t = (double)i / (double)steps;
        int r, g, b;
        if (t < 0.55) {
            double u = t / 0.55;
            r = (int)(15 + (49 - 15) * u);
            g = (int)(23 + (27 - 23) * u);
            b = (int)(42 + (88 - 42) * u);
        } else {
            double u = (t - 0.55) / 0.45;
            r = (int)(49 + (14 - 49) * u);
            g = (int)(27 + (116 - 27) * u);
            b = (int)(88 + (144 - 88) * u);
        }
        RECT slice = {x0, 0, x1 + 1, 83};
        HBRUSH br = CreateSolidBrush(RGB(r, g, b));
        FillRect(hdc, &slice, br);
        DeleteObject(br);
    }

    /* Ruban lumineux cyan/magenta sous la bannière */
    RECT rcAccent = {0, 83, rcClient.right, 86};
    HBRUSH brAcc = CreateSolidBrush(RGB(56, 189, 248));
    FillRect(hdc, &rcAccent, brAcc);
    DeleteObject(brAcc);

    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(248, 250, 252));
    HGDIOBJ oldF = SelectObject(hdc, g_fontTitle);
    RECT rcTitle = {22, 16, rcClient.right - 20, 48};
    DrawTextW(hdc, L"\x03A9  Omega Code Studio v2.0", -1, &rcTitle, DT_LEFT | DT_VCENTER | DT_SINGLELINE);

    SetTextColor(hdc, RGB(186, 230, 253));
    SelectObject(hdc, g_fontSub);
    RECT rcSub = {24, 48, rcClient.right - 20, 74};
    DrawTextW(
        hdc,
        L"Installation complète autonome — IDE Algorithmique Moderne (successeur d'Alg_32)",
        -1,
        &rcSub,
        DT_LEFT | DT_VCENTER | DT_SINGLELINE
    );
    SelectObject(hdc, oldF);
}

static LRESULT CALLBACK SetupWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_CREATE: {
        g_fontTitle = CreateFontW(
            -22, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI"
        );
        g_fontSub = CreateFontW(
            -13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI"
        );
        g_fontUI = CreateFontW(
            -14, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI"
        );

        HWND lblDir = CreateWindowExW(
            0, L"STATIC", L"Dossier d'installation (aucun droit Administrateur requis) :",
            WS_CHILD | WS_VISIBLE, 24, 102, 530, 20, hwnd, NULL, NULL, NULL
        );
        SendMessageW(lblDir, WM_SETFONT, (WPARAM)g_fontUI, TRUE);

        g_editDir = CreateWindowExW(
            WS_EX_CLIENTEDGE, L"EDIT", g_opts.installDir,
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL, 24, 126, 430, 28,
            hwnd, (HMENU)ID_EDIT_DIR, NULL, NULL
        );
        SendMessageW(g_editDir, WM_SETFONT, (WPARAM)g_fontUI, TRUE);

        g_btnBrowse = CreateWindowExW(
            0, L"BUTTON", L"Parcourir...",
            WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 464, 125, 110, 30,
            hwnd, (HMENU)ID_BTN_BROWSE, NULL, NULL
        );
        SendMessageW(g_btnBrowse, WM_SETFONT, (WPARAM)g_fontUI, TRUE);

        g_chkDesktop = CreateWindowExW(
            0, L"BUTTON", L"Créer un raccourci « Omega Code Studio » sur le Bureau",
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 24, 170, 540, 24,
            hwnd, (HMENU)ID_CHK_DESKTOP, NULL, NULL
        );
        g_chkStartMenu = CreateWindowExW(
            0, L"BUTTON", L"Ajouter au Menu Démarrer de Windows",
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 24, 198, 540, 24,
            hwnd, (HMENU)ID_CHK_STARTMENU, NULL, NULL
        );
        g_chkAssoc = CreateWindowExW(
            0, L"BUTTON", L"Associer automatiquement les fichiers d'algorithmes (.alg)",
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 24, 226, 540, 24,
            hwnd, (HMENU)ID_CHK_ASSOC, NULL, NULL
        );
        g_chkLaunch = CreateWindowExW(
            0, L"BUTTON", L"Lancer Omega Code Studio dès la fin de l'installation",
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 24, 254, 540, 24,
            hwnd, (HMENU)ID_CHK_LAUNCH, NULL, NULL
        );

        HWND checks[4] = {g_chkDesktop, g_chkStartMenu, g_chkAssoc, g_chkLaunch};
        for (int k = 0; k < 4; ++k) {
            SendMessageW(checks[k], WM_SETFONT, (WPARAM)g_fontUI, TRUE);
            SendMessageW(checks[k], BM_SETCHECK, BST_CHECKED, 0);
        }

        g_lblStatus = CreateWindowExW(
            0, L"STATIC", g_statusText,
            WS_CHILD | WS_VISIBLE, 24, 294, 550, 22,
            hwnd, (HMENU)ID_LBL_STATUS, NULL, NULL
        );
        SendMessageW(g_lblStatus, WM_SETFONT, (WPARAM)g_fontUI, TRUE);

        g_progress = CreateWindowExW(
            0, PROGRESS_CLASSW, NULL,
            WS_CHILD | WS_VISIBLE | PBS_SMOOTH, 24, 320, 550, 22,
            hwnd, (HMENU)ID_PROGRESS, NULL, NULL
        );
        SendMessageW(g_progress, PBM_SETRANGE, 0, MAKELPARAM(0, 100));
        SendMessageW(g_progress, PBM_SETPOS, 0, 0);

        g_btnInstall = CreateWindowExW(
            0, L"BUTTON", L"Installer maintenant",
            WS_CHILD | WS_VISIBLE | BS_DEFPUSHBUTTON, 304, 362, 160, 34,
            hwnd, (HMENU)ID_BTN_INSTALL, NULL, NULL
        );
        SendMessageW(g_btnInstall, WM_SETFONT, (WPARAM)g_fontUI, TRUE);

        g_btnCancel = CreateWindowExW(
            0, L"BUTTON", L"Quitter",
            WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 474, 362, 100, 34,
            hwnd, (HMENU)ID_BTN_CANCEL, NULL, NULL
        );
        SendMessageW(g_btnCancel, WM_SETFONT, (WPARAM)g_fontUI, TRUE);
        return 0;
    }

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        paint_header_banner(hdc, rc);
        EndPaint(hwnd, &ps);
        return 0;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdcStatic = (HDC)wParam;
        SetBkColor(hdcStatic, RGB(248, 250, 252));
        SetTextColor(hdcStatic, RGB(15, 23, 42));
        return (INT_PTR)g_bgBrush;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == ID_BTN_BROWSE) {
            browse_for_folder(hwnd);
        } else if (id == ID_BTN_INSTALL) {
            start_installation(hwnd);
        } else if (id == ID_BTN_CANCEL) {
            if (g_installing) {
                g_cancelReq = 1;
            } else {
                DestroyWindow(hwnd);
            }
        }
        return 0;
    }

    case WM_APP_PROGRESS: {
        SendMessageW(g_progress, PBM_SETPOS, wParam, 0);
        SetWindowTextW(g_lblStatus, g_statusText);
        return 0;
    }

    case WM_APP_DONE: {
        InterlockedExchange(&g_installing, 0);
        if (wParam == 1) {
            SendMessageW(g_progress, PBM_SETPOS, 100, 0);
            SetWindowTextW(g_lblStatus, L"Installation réussie !");
            if (g_opts.launchAfter) {
                wchar_t mainExe[MAX_PATH * 2];
                wsprintfW(mainExe, L"%s\\OmegaCodeStudio.exe", g_opts.installDir);
                ShellExecuteW(NULL, L"open", mainExe, NULL, g_opts.installDir, SW_SHOWNORMAL);
            } else {
                MessageBoxW(
                    hwnd,
                    L"Omega Code Studio v2.0 a été installé avec succès !\n"
                    L"Vous pouvez le lancer depuis votre Bureau ou le Menu Démarrer.",
                    L"Omega Code Studio — Installation terminée",
                    MB_OK | MB_ICONINFORMATION
                );
            }
            DestroyWindow(hwnd);
        } else {
            MessageBoxW(hwnd, g_errorText, L"Omega Code Studio — Erreur", MB_OK | MB_ICONERROR);
            EnableWindow(g_editDir, TRUE);
            EnableWindow(g_btnBrowse, TRUE);
            EnableWindow(g_chkDesktop, TRUE);
            EnableWindow(g_chkStartMenu, TRUE);
            EnableWindow(g_chkAssoc, TRUE);
            EnableWindow(g_chkLaunch, TRUE);
            EnableWindow(g_btnInstall, TRUE);
        }
        return 0;
    }

    case WM_CLOSE:
        if (g_installing) {
            g_cancelReq = 1;
            return 0;
        }
        DestroyWindow(hwnd);
        return 0;

    case WM_DESTROY:
        if (g_fontTitle) DeleteObject(g_fontTitle);
        if (g_fontSub) DeleteObject(g_fontSub);
        if (g_fontUI) DeleteObject(g_fontUI);
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE hPrev, PWSTR lpCmdLine, int nCmdShow) {
    (void)hPrev;

    INITCOMMONCONTROLSEX icc;
    icc.dwSize = sizeof(icc);
    icc.dwICC = ICC_PROGRESS_CLASS | ICC_STANDARD_CLASSES;
    InitCommonControlsEx(&icc);

    /* Dossier d'installation par défaut : %LOCALAPPDATA%\Programs\OmegaCodeStudio */
    wchar_t localAppData[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, localAppData))) {
        wsprintfW(g_opts.installDir, L"%s\\Programs\\OmegaCodeStudio", localAppData);
    } else {
        wcscpy(g_opts.installDir, L"C:\\OmegaCodeStudio");
    }

    g_opts.makeDesktop = TRUE;
    g_opts.makeStartMenu = TRUE;
    g_opts.assocAlg = TRUE;
    g_opts.launchAfter = FALSE;
    g_opts.silentMode = (lpCmdLine && (wcsstr(lpCmdLine, L"/S") || wcsstr(lpCmdLine, L"--silent")));

    if (g_opts.silentMode) {
        return (int)install_worker_thread(NULL);
    }

    g_opts.launchAfter = TRUE;
    g_bgBrush = CreateSolidBrush(RGB(248, 250, 252));

    WNDCLASSEXW wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = SetupWndProc;
    wc.hInstance = hInst;
    wc.hIcon = LoadIconW(hInst, MAKEINTRESOURCEW(1));
    wc.hCursor = LoadCursorW(NULL, IDC_ARROW);
    wc.hbrBackground = g_bgBrush;
    wc.lpszClassName = L"OmegaCodeStudioSetupWnd";
    RegisterClassExW(&wc);

    int winW = 606;
    int winH = 448;
    int sx = (GetSystemMetrics(SM_CXSCREEN) - winW) / 2;
    int sy = (GetSystemMetrics(SM_CYSCREEN) - winH) / 2;

    g_hwnd = CreateWindowExW(
        0,
        wc.lpszClassName,
        L"Installation d'Omega Code Studio v2.0 (Windows 64 bits)",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        sx, sy, winW, winH,
        NULL, NULL, hInst, NULL
    );

    ShowWindow(g_hwnd, nCmdShow);
    UpdateWindow(g_hwnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        if (!IsDialogMessageW(g_hwnd, &msg)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    DeleteObject(g_bgBrush);
    return (int)msg.wParam;
}
