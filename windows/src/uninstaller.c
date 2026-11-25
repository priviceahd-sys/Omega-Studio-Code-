/*
 * Uninstall-OmegaCodeStudio.exe — Désinstallateur natif Windows x86_64
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shlobj.h>
#include <wchar.h>

static void delete_tree_recursive(const wchar_t *dir) {
    wchar_t pattern[MAX_PATH * 2];
    wsprintfW(pattern, L"%s\\*", dir);

    WIN32_FIND_DATAW fd;
    HANDLE hFind = FindFirstFileW(pattern, &fd);
    if (hFind == INVALID_HANDLE_VALUE) return;

    do {
        if (wcscmp(fd.cFileName, L".") == 0 || wcscmp(fd.cFileName, L"..") == 0)
            continue;
        wchar_t sub[MAX_PATH * 2];
        wsprintfW(sub, L"%s\\%s", dir, fd.cFileName);
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            delete_tree_recursive(sub);
            RemoveDirectoryW(sub);
        } else {
            SetFileAttributesW(sub, FILE_ATTRIBUTE_NORMAL);
            DeleteFileW(sub);
        }
    } while (FindNextFileW(hFind, &fd));

    FindClose(hFind);
}

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE hPrev, PWSTR lpCmd, int nShow) {
    (void)hInst; (void)hPrev; (void)lpCmd; (void)nShow;

    int ans = MessageBoxW(
        NULL,
        L"Voulez-vous désinstaller Omega Code Studio de votre ordinateur Windows ?\n\n"
        L"(Vos fichiers d'algorithmes personnels .alg ne seront pas supprimés.)",
        L"Désinstallation d'Omega Code Studio",
        MB_YESNO | MB_ICONQUESTION
    );
    if (ans != IDYES) {
        return 0;
    }

    wchar_t exePath[MAX_PATH * 2];
    GetModuleFileNameW(NULL, exePath, MAX_PATH * 2);
    wchar_t appDir[MAX_PATH * 2];
    wcscpy(appDir, exePath);
    wchar_t *slash = wcsrchr(appDir, L'\\');
    if (slash) *slash = L'\0';

    /* 1. Raccourci Bureau */
    wchar_t desktopDir[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_DESKTOPDIRECTORY, NULL, 0, desktopDir))) {
        wchar_t lnk[MAX_PATH * 2];
        wsprintfW(lnk, L"%s\\Omega Code Studio.lnk", desktopDir);
        DeleteFileW(lnk);
    }

    /* 2. Menu Démarrer */
    wchar_t programsDir[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAMS, NULL, 0, programsDir))) {
        wchar_t smDir[MAX_PATH * 2];
        wsprintfW(smDir, L"%s\\Omega Code Studio", programsDir);
        delete_tree_recursive(smDir);
        RemoveDirectoryW(smDir);
    }

    /* 3. Nettoyage du Registre utilisateur (HKCU) */
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\OmegaCodeStudio.alg");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OmegaCodeStudio");

    HKEY hAlg = NULL;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Classes\\.alg", 0, KEY_READ, &hAlg) == ERROR_SUCCESS) {
        wchar_t val[128] = {0};
        DWORD sz = sizeof(val);
        if (RegQueryValueExW(hAlg, NULL, NULL, NULL, (LPBYTE)val, &sz) == ERROR_SUCCESS) {
            RegCloseKey(hAlg);
            if (wcscmp(val, L"OmegaCodeStudio.alg") == 0) {
                RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\.alg");
            }
        } else {
            RegCloseKey(hAlg);
        }
    }

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);

    MessageBoxW(
        NULL,
        L"Omega Code Studio a été désinstallé avec succès.",
        L"Omega Code Studio",
        MB_OK | MB_ICONINFORMATION
    );

    /* 4. Suppression différée du dossier d'installation (y compris cet exécutable) */
    wchar_t cmd[MAX_PATH * 3];
    wsprintfW(cmd, L"cmd.exe /c ping 127.0.0.1 -n 2 > nul & rmdir /s /q \"%s\"", appDir);
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, L"C:\\", &si, &pi)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    }

    return 0;
}
