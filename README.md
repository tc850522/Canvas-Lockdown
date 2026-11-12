# Canvas Homework Enforcer

## 🔑 How to Get a Canvas Access Token
To allow the application to securely check your upcoming homework, you must generate a personal access token directly from your Canvas account:

1. Log into your school's Canvas portal in your web browser.
2. Navigate to your **Account Settings**.
3. Scroll down to find the **Approved Integrations** section.
4. Click the **New Access Token** button.
5. Copy the generated token string and save it securely, as it provides full programmatic access to your account and will only be shown once.

## 🚀 How to Run the Code

**Prerequisites:** Ensure you have Python installed, the `requests` library installed, and a C++ compiler (like MinGW-w64) set up on your Windows system.

### Step 1: Install Python Dependencies
Open your standard PowerShell or terminal and install the required library:
```bash
pip install requests
```

### Step 2: Compile the C++ Enforcer
Navigate to your project directory in PowerShell and compile the C++ background daemon into an executable file:
```bash
g++ enforcer.cpp -o enforcer.exe
```
*(Note: If your file is named differently, such as `enforcer_2.cpp` or `enforcer_3.cpp`, replace `enforcer.cpp` with your exact file name.)*

### Step 3: Launch the Application (As Administrator)
Because the C++ enforcer requires elevated system privileges to forcefully close unauthorized background processes, the Python GUI must be run with administrative rights so it can launch the daemon correctly.

1. Right-click your Start button and select **Windows PowerShell (Admin)** to open an elevated terminal.
2. Navigate to your project folder using the `cd` command.
3. Start the graphical interface by running: `python canvas_lockdown.py`.
4. In the app window, enter your Canvas domain, paste your Access Token, set your expiration date, and choose your lookahead days.
5. Click **Confirm & Start Enforcer**. The app will automatically launch `enforcer.exe` in the background and begin monitoring your system based on your Canvas assignments.