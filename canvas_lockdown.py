import tkinter as tk
from tkinter import messagebox
import requests
import threading
import time
import json
import os
from datetime import datetime, timedelta
import subprocess

class CanvasLockdownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Canvas Homework Enforcer")
        self.root.geometry("400x500")
        
        # State variables
        self.is_locked = False
        self.is_confirmed = False
        self.is_paused = False
        self.pause_until = 0
        self.running = True
        
        self.build_gui()
        self.load_config() # Automatically load saved settings on startup

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
        self.days_entry.pack()

        self.confirm_btn = tk.Button(self.root, text="Confirm & Start Enforcer", command=self.start_enforcer, bg="lightblue")
        self.confirm_btn.pack(pady=15)

        self.status_label = tk.Label(self.root, text="Status: Waiting for Input", fg="gray", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=10)

        self.pause_btn = tk.Button(self.root, text="Pause Lockdown (1 Hour)", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(pady=10)

    def load_config(self):
        """Loads saved inputs from config.json to populate the GUI text boxes."""
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    config_data = json.load(f)
                    
                # Populate entry fields if the keys exist
                if "domain" in config_data:
                    self.domain_entry.insert(0, config_data["domain"])
                if "token" in config_data:
                    self.token_entry.insert(0, config_data["token"])
                if "expire_date" in config_data:
                    self.expire_entry.insert(0, config_data["expire_date"])
                if "days" in config_data:
                    self.days_entry.insert(0, config_data["days"])
                else:
                    self.days_entry.insert(0, "0")
            except Exception as e:
                print(f"Failed to load config: {e}")
        else:
            self.days_entry.insert(0, "0")

    def write_config(self):
        """Writes the current state AND the user's text inputs to config.json."""
        config_data = {
            "is_locked": self.is_locked,
            "pause_until": self.pause_until,
            "domain": self.domain_entry.get().strip(),
            "token": self.token_entry.get().strip(),
            "expire_date": self.expire_entry.get().strip(),
            "days": self.days_entry.get().strip()
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Config write error: {e}")

    def start_enforcer(self):
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
        
        # Save inputs to file immediately
        self.write_config()

        self.api_thread = threading.Thread(target=self.poll_canvas_api, daemon=True)
        self.api_thread.start()

        try:
            subprocess.Popen(["enforcer.exe"])
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to start enforcer.exe: {e}\nEnsure it is compiled and in the same folder.")

    def toggle_pause(self):
        if not self.is_paused:
            self.pause_until = int(time.time()) + 3600
            self.is_paused = True
            self.status_label.config(text="Status: PAUSED (1 Hour)", fg="orange")
            self.pause_btn.config(text="Unpause Lockdown")
            self.write_config()
        else:
            self.pause_until = 0
            self.is_paused = False
            self.pause_btn.config(text="Pause Lockdown (1 Hour)")
            self.update_ui_state()
            self.write_config()

    def poll_canvas_api(self):
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
        
        if not self.is_paused:
            self.update_ui_state()

    def update_ui_state(self):
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
