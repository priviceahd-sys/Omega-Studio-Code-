/*
 * OmegaCodeStudio.exe — Lanceur natif Windows x86_64 GUI (sans fenêtre console)
 * Démarre le runtime Python 3.12 + PyQt6 embarqué et transmet tout fichier .alg ouvert.
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE hPrev, PWSTR lpCmdLine, int nCmdShow) {
    (void)hInst;
    (void)hPrev;
    (void)nCmdShow;

    wchar_t exePath[MAX_PATH * 2];
    DWORD len = GetModuleFileNameW(NULL, exePath, MAX_PATH * 2);
    if (len == 0 || len >= MAX_PATH * 2) {
        return 1;
    }

    /* Répertoire racine de l'installation */
    wchar_t appDir[MAX_PATH * 2];
    wcscpy(appDir, exePath);
    wchar_t *lastSlash = wcsrchr(appDir, L'\\');
    if (lastSlash) {
        *lastSlash = L'\0';
    }

    wchar_t pythonwPath[MAX_PATH * 2];
    wsprintfW(pythonwPath, L"%s\\runtime\\pythonw.exe", appDir);

    if (GetFileAttributesW(pythonwPath) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(
            NULL,
            L"Le moteur Python embarqué (runtime\\pythonw.exe) est introuvable.\n"
            L"Veuillez réinstaller Omega Code Studio.",
            L"Omega Code Studio — Erreur de lancement",
            MB_OK | MB_ICONERROR
        );
        return 2;
    }

    SetEnvironmentVariableW(L"OMEGA_APP_NAME", L"Omega Code Studio");
    SetEnvironmentVariableW(L"OMEGA_DESKTOP_ID", L"omega-code-studio");
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"PYTHONDONTWRITEBYTECODE", L"1");
    SetEnvironmentVariableW(L"PYTHONPATH", appDir);

    wchar_t cmdBuf[8192];
    if (lpCmdLine && lpCmdLine[0] != L'\0') {
        wsprintfW(cmdBuf, L"\"%s\" -m omega_studio %s", pythonwPath, lpCmdLine);
    } else {
        wsprintfW(cmdBuf, L"\"%s\" -m omega_studio", pythonwPath);
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    BOOL ok = CreateProcessW(
        pythonwPath,
        cmdBuf,
        NULL,
        NULL,
        FALSE,
        CREATE_NO_WINDOW,
        NULL,
        appDir,
        &si,
        &pi
    );

    if (!ok) {
        MessageBoxW(
            NULL,
            L"Impossible de démarrer Omega Code Studio.",
            L"Omega Code Studio",
            MB_OK | MB_ICONERROR
        );
        return 3;
    }

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
