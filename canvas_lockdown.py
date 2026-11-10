import tkinter as tk
from tkinter import messagebox
import requests
import threading
import time
import json
from datetime import datetime, timedelta
import subprocess # Added to start the enforcer.exe

class CanvasLockdownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Canvas Homework Enforcer")
        self.root.geometry("400x500")
        
        # State variables
        self.is_locked = False
        self.is_confirmed = False
        self.is_paused = False # New state variable for tracking pause toggle
        self.pause_until = 0
        self.running = True
        
        self.build_gui()

    def build_gui(self):
        tk.Label(self.root, text="Canvas Domain (e.g., https://canvas.edu):").pack(pady=5)
        self.domain_entry = tk.Entry(self.root, width=40)
        self.domain_entry.pack()

        tk.Label(self.root, text="API Access Token:").pack(pady=5)
        self.token_entry = tk.Entry(self.root, width=40, show="*")
        self.token_entry.pack()

        tk.Label(self.root, text="API Token Expiration Date (YYYY-MM-DD):").pack(pady=5)
        self.expire_entry = tk.Entry(self.root, width=20)
        self.expire_entry.pack()

        tk.Label(self.root, text="Lockdown if due within (Days):").pack(pady=5)
        self.days_entry = tk.Entry(self.root, width=10)
        self.days_entry.insert(0, "0") 
        self.days_entry.pack()

        # The Confirm & Start button
        self.confirm_btn = tk.Button(self.root, text="Confirm & Start Enforcer", command=self.start_enforcer, bg="lightblue")
        self.confirm_btn.pack(pady=15)

        self.status_label = tk.Label(self.root, text="Status: Waiting for Input", fg="gray", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=10)

        # Pause/Unpause toggle button
        self.pause_btn = tk.Button(self.root, text="Pause Lockdown (1 Hour)", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(pady=10)

    def start_enforcer(self):
        """Validates input, starts the polling thread, and launches the C++ Daemon."""
        domain = self.domain_entry.get().strip()
        token = self.token_entry.get().strip()
        days = self.days_entry.get().strip()
        expire_date = self.expire_entry.get().strip()

        if not domain or not token or not days.isdigit() or not expire_date:
            messagebox.showwarning("Missing Input", "Please fill in all fields before confirming.")
            return
            
        try:
            exp_date_obj = datetime.strptime(expire_date, "%Y-%m-%d").date()
            if exp_date_obj < datetime.now().date():
                messagebox.showerror("Token Expired", "Your API token is already past its expiration date!")
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Please format the expiration date as YYYY-MM-DD.")
            return

        self.is_confirmed = True
        self.confirm_btn.config(state=tk.DISABLED, text="Enforcer Running...")
        self.status_label.config(text="Status: Unlocked", fg="green")
        
        # Start background API polling thread
        self.api_thread = threading.Thread(target=self.poll_canvas_api, daemon=True)
        self.api_thread.start()

        # Automatically start the C++ enforcer.exe process
        try:
            # Note: This assumes enforcer.exe is in the same directory.
            # You must have launched the Python script as Administrator for the enforcer to inherit admin rights.
            subprocess.Popen(["enforcer.exe"])
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to start enforcer.exe: {e}\nEnsure it is compiled and in the same folder.")

    def toggle_pause(self):
        """Toggles between paused and unpaused states."""
        if not self.is_paused:
            # Activate Pause
            self.pause_until = int(time.time()) + 3600
            self.is_paused = True
            self.status_label.config(text="Status: PAUSED (1 Hour)", fg="orange")
            self.pause_btn.config(text="Unpause Lockdown")
            self.write_config()
        else:
            # Unpause manually before the timer is up
            self.pause_until = 0
            self.is_paused = False
            self.pause_btn.config(text="Pause Lockdown (1 Hour)")
            # Trigger an immediate UI update based on the current lock state
            self.update_ui_state()
            self.write_config()

    def write_config(self):
        """Writes the current state to a shared JSON file for the C++ Enforcer."""
        config_data = {
            "is_locked": self.is_locked,
            "pause_until": self.pause_until
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config_data, f)
        except Exception as e:
            print(f"Config write error: {e}")

    def poll_canvas_api(self):
        """Background loop to check Canvas API every 60 seconds."""
        while self.running and self.is_confirmed:
            domain = self.domain_entry.get().strip()
            token = self.token_entry.get().strip()
            days_in_advance = self.days_entry.get().strip()
            
            url = f"{domain}/api/v1/users/self/todo"
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    tasks = response.json()
                    self.evaluate_tasks(tasks, int(days_in_advance))
            except Exception as e:
                print(f"API Error: {e}")
            
            time.sleep(60) 

    def evaluate_tasks(self, tasks, days_in_advance):
        today = datetime.now().astimezone().date()
        target_date = today + timedelta(days=days_in_advance)
        
        needs_lockdown = False
        
        for item in tasks:
            if 'assignment' in item and item['assignment']['due_at']:
                due_at_str = item['assignment']['due_at']
                
                utc_due_obj = datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
                local_due_date = utc_due_obj.astimezone().date()
                
                if local_due_date <= target_date:
                    needs_lockdown = True
                    break
        
        self.is_locked = needs_lockdown
        self.write_config()
        
        # Only auto-update the UI if we aren't actively paused
        if not self.is_paused:
            self.update_ui_state()

    def update_ui_state(self):
        # Handle the automatic expiration of the 1-hour pause
        if self.is_paused and time.time() > self.pause_until:
            self.is_paused = False
            self.pause_until = 0
            self.pause_btn.config(text="Pause Lockdown (1 Hour)")

        if self.is_paused:
            return
            
        if self.is_locked:
            self.status_label.config(text="Status: LOCKED DOWN", fg="red")
            self.pause_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Status: Unlocked", fg="green")
            self.pause_btn.config(state=tk.DISABLED)

    def on_closing(self):
        self.running = False
        self.is_locked = False
        self.write_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CanvasLockdownApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
