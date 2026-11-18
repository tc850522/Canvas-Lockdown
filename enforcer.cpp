#include <windows.h>
#include <tlhelp32.h>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>
#include <thread>

std::wstring toLowerCase(std::wstring str) {
    std::transform(str.begin(), str.end(), str.begin(), ::towlower);
    return str;
}

// Gets the directory where enforcer.exe is located so config.json is always found on boot
std::string getConfigPath() {
    char buffer[MAX_PATH];
    GetModuleFileNameA(NULL, buffer, MAX_PATH);
    std::string exePath(buffer);
    size_t lastSlash = exePath.find_last_of("\\/");
    if (lastSlash != std::string::npos) {
        return exePath.substr(0, lastSlash + 1) + "config.json";
    }
    return "config.json";
}

bool isAuthorized(const std::wstring& procName) {
    std::vector<std::wstring> whitelist = {
        // The Enforcer Itself
        L"enforcer.exe",

        // Educational / Authorized Apps
        L"code.exe", L"cmd.exe", L"powershell.exe",
        L"chrome.exe", L"firefox.exe", L"msedge.exe",
        L"python.exe", L"pythonw.exe",

        // Critical Windows OS Processes
        L"explorer.exe", L"svchost.exe", L"taskmgr.exe", L"conhost.exe",
        L"csrss.exe", L"smss.exe", L"wininit.exe", L"winlogon.exe",
        L"services.exe", L"lsass.exe", L"dwm.exe", L"fontdrvhost.exe",
        L"sihost.exe", L"ctfmon.exe", L"runtimebroker.exe", L"wmiprvse.exe",
        L"searchapp.exe", L"searchhost.exe", L"startmenuexperiencehost.exe"
    };
    for (const auto& allowed : whitelist) {
        if (procName == allowed) return true;
    }
    return false;
}

void enforceLockdown() {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return;

    PROCESSENTRY32W pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32W);

    if (Process32FirstW(hSnap, &pe32)) {
        do {
            std::wstring procName = toLowerCase(pe32.szExeFile);

            if (pe32.th32ProcessID == 0 || pe32.th32ProcessID == 4) continue;

            if (!isAuthorized(procName)) {
                HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pe32.th32ProcessID);
                if (hProcess != NULL) {
                    TerminateProcess(hProcess, 9);
                    CloseHandle(hProcess);
                    std::wcout << L"Terminated unauthorized app: " << procName << std::endl;
                }
            }
        } while (Process32NextW(hSnap, &pe32));
    }
    CloseHandle(hSnap);
}

void checkConfigAndEnforce() {
    std::string configPath = getConfigPath();

    while (true) {
        std::ifstream configFile(configPath);
        if (configFile.is_open()) {
            std::string content((std::istreambuf_iterator<char>(configFile)), std::istreambuf_iterator<char>());

            bool isLocked = (content.find("\"is_locked\": true") != std::string::npos);

            size_t pausePos = content.find("\"pause_until\": ");
            long long pauseUntil = 0;
            try {
                if (pausePos != std::string::npos && pausePos + 15 < content.length()) {
                    std::string numStr = content.substr(pausePos + 15);
                    pauseUntil = std::stoll(numStr);
                }
            } catch (...) {
                // Ignore partial writes while Python updates config.json
            }

            auto now = std::chrono::system_clock::now();
            auto duration = now.time_since_epoch();
            long long currentTimestamp = std::chrono::duration_cast<std::chrono::seconds>(duration).count();

            if (isLocked && currentTimestamp > pauseUntil) {
                enforceLockdown();
            }
        }
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }
}

int main() {
    std::cout << "Starting C++ OS Enforcer Daemon..." << std::endl;
    checkConfigAndEnforce();
    return 0;
}