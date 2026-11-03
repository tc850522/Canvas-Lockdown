#include <windows.h>
#include <tlhelp32.h>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>
#include <thread>

// Helper function to handle case-insensitive process names
std::wstring toLowerCase(std::wstring str) {
    std::transform(str.begin(), str.end(), str.begin(), ::towlower);
    return str;
}

// Defines exactly what "doing homework" means by building a whitelist[cite: 4]
bool isAuthorized(const std::wstring& procName) {
    std::vector<std::wstring> whitelist = {
        L"code.exe", L"cmd.exe", L"powershell.exe", 
        L"chrome.exe", L"firefox.exe", L"msedge.exe",
        L"python.exe", L"explorer.exe", L"svchost.exe",
        L"taskmgr.exe", L"conhost.exe"
    };
    for (const auto& allowed : whitelist) {
        if (procName == allowed) return true;
    }
    return false;
}

// Actively monitors and kills unauthorized processes[cite: 4]
void enforceLockdown() {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return;

    PROCESSENTRY32W pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32W);

    if (Process32FirstW(hSnap, &pe32)) {
        do {
            std::wstring procName = toLowerCase(pe32.szExeFile);
            
            // Skip protecting critical system processes like Idle and System for safety
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

// Background loop to poll the Python GUI's configuration file[cite: 4]
void checkConfigAndEnforce() {
    while (true) {
        std::ifstream configFile("config.json");
        if (configFile.is_open()) {
            std::string content((std::istreambuf_iterator<char>(configFile)), std::istreambuf_iterator<char>());
            
            // Basic string parsing to read the Python JSON output without external C++ libraries
            bool isLocked = (content.find("\"is_locked\": true") != std::string::npos);
            
            size_t pausePos = content.find("\"pause_until\": ");
            long long pauseUntil = 0;
            if (pausePos != std::string::npos) {
                std::string numStr = content.substr(pausePos + 15);
                pauseUntil = std::stoll(numStr);
            }

            // Get current timestamp
            auto now = std::chrono::system_clock::now();
            auto duration = now.time_since_epoch();
            long long currentTimestamp = std::chrono::duration_cast<std::chrono::seconds>(duration).count();

            // Enforce only if locked AND the 1-hour pause timer has passed
            if (isLocked && currentTimestamp > pauseUntil) {
                enforceLockdown();
            }
        }
        std::this_thread::sleep_for(std::chrono::seconds(5)); // Sweep the system every 5 seconds[cite: 2]
    }
}

int main() {
    std::cout << "Starting C++ OS Enforcer Daemon..." << std::endl;
    checkConfigAndEnforce();
    return 0;
}