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
        self.root.geometry("400x520")
        
        # State variables
        self.is_locked = False
        self.is_confirmed = False
        self.is_paused = False
        self.pause_until = 0
        self.running = True
        self.enforcer_proc = None
        
        # Thread-safe cached settings
        self.domain = ""
        self.token = ""
        self.days_or_date = "0"
        
        self.build_gui()
        self.load_config()

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

        tk.Label(self.root, text="Lockdown if due within (Days OR YYYY-MM-DD):").pack(pady=5)
        self.days_entry = tk.Entry(self.root, width=20)
        self.days_entry.pack()

        self.confirm_btn = tk.Button(
            self.root,
            text="Confirm & Start Enforcer",
            command=self.start_enforcer,
            bg="lightblue"
        )
        self.confirm_btn.pack(pady=15)

        self.status_label = tk.Label(
            self.root,
            text="Status: Waiting for Input",
            fg="gray",
            font=("Arial", 14, "bold")
        )
        self.status_label.pack(pady=10)

        self.pause_btn = tk.Button(
            self.root,
            text="Pause Lockdown (1 Hour)",
            command=self.toggle_pause,
            state=tk.DISABLED
        )
        self.pause_btn.pack(pady=10)

    def parse_target_date(self, value_str):
        """Accepts either an integer number of days (e.g. '7') or a date ('YYYY-MM-DD')."""
        today = datetime.now().astimezone().date()
        if value_str.isdigit():
            return today + timedelta(days=int(value_str))
        try:
            return datetime.strptime(value_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    def load_config(self):
        """Loads saved inputs from config.json to populate the GUI text boxes."""
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    config_data = json.load(f)
                    
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
            "domain": self.domain,
            "token": self.token,
            "expire_date": self.expire_entry.get().strip(),
            "days": self.days_or_date
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Config write error: {e}")

    def start_enforcer(self):
        domain = self.domain_entry.get().strip().rstrip("/")
        token = self.token_entry.get().strip()
        days_or_date = self.days_entry.get().strip()
        expire_date = self.expire_entry.get().strip()

        if not domain or not token or not days_or_date or not expire_date:
            messagebox.showwarning("Missing Input", "Please fill in all fields before confirming.")
            return

        target_date = self.parse_target_date(days_or_date)
        if target_date is None:
            messagebox.showerror(
                "Invalid Lookahead",
                "Enter either a whole number of days (e.g., 7) or a date (YYYY-MM-DD)."
            )
            return
            
        try:
            exp_date_obj = datetime.strptime(expire_date, "%Y-%m-%d").date()
            if exp_date_obj < datetime.now().date():
                messagebox.showerror("Token Expired", "Your API token is already past its expiration date!")
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Please format the expiration date as YYYY-MM-DD.")
            return

        self.domain = domain
        self.token = token
        self.days_or_date = days_or_date
        self.write_config()

        # Launch enforcer.exe if it isn't already running
        if self.enforcer_proc is None or self.enforcer_proc.poll() is not None:
            try:
                enforcer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enforcer.exe")
                if not os.path.exists(enforcer_path):
                    enforcer_path = "enforcer.exe"
                self.enforcer_proc = subprocess.Popen(
                    [enforcer_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            except Exception as e:
                messagebox.showerror(
                    "Execution Error",
                    f"Failed to start enforcer.exe: {e}\nEnsure it is compiled and in the same folder."
                )

        if not self.is_confirmed:
            self.is_confirmed = True
            self.confirm_btn.config(text="Update Settings & Re-check Now")
            self.api_thread = threading.Thread(target=self.poll_canvas_api, daemon=True)
            self.api_thread.start()
        else:
            # Trigger an immediate check when the user updates the date/days
            threading.Thread(target=self.check_once, daemon=True).start()

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

    def check_once(self):
        today = datetime.now().astimezone().date()
        target_date = self.parse_target_date(self.days_or_date)
        if target_date is None:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        # Use Canvas Planner API so future assignments beyond 7 days are included
        url = f"{self.domain}/api/v1/planner/items"
        params = {
            "start_date": today.isoformat(),
            "end_date": (target_date + timedelta(days=1)).isoformat(),
            "per_page": 50
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                items = response.json()
                self.evaluate_tasks(items, today, target_date)
            else:
                print(f"Canvas API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"API Error: {e}")

    def poll_canvas_api(self):
        while self.running and self.is_confirmed:
            self.check_once()
            time.sleep(60)

    def evaluate_tasks(self, items, today, target_date):
        needs_lockdown = False
        homework_types = {"assignment", "quiz", "discussion_topic", "sub_assignment"}
        
        print(f"\nChecking homework due between {today} and {target_date}...")
        
        for item in items:
            # Support both /api/v1/planner/items and /api/v1/users/self/todo formats
            if "plannable_type" in item:
                if item.get("plannable_type") not in homework_types:
                    continue
                
                # Skip if manually marked complete on the Canvas planner
                override = item.get("planner_override")
                if isinstance(override, dict) and override.get("marked_complete"):
                    continue
                
                # Skip if already submitted
                subs = item.get("submissions")
                if isinstance(subs, dict) and subs.get("submitted"):
                    continue
                
                plannable = item.get("plannable", {})
                due_at_str = plannable.get("due_at") or item.get("plannable_date")
                name = plannable.get("title") or plannable.get("name") or "Unnamed Task"
            elif "assignment" in item and item["assignment"].get("due_at"):
                due_at_str = item["assignment"]["due_at"]
                name = item["assignment"].get("name", "Unnamed Assignment")
            else:
                continue

            if not due_at_str:
                continue

            utc_due_obj = datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
            local_due_obj = utc_due_obj.astimezone()
            local_due_date = local_due_obj.date()
            
            print(f" - Found: '{name}' | Local Due Date: {local_due_date}")
            
            if today <= local_due_date <= target_date:
                print(f"--> LOCKDOWN TRIGGERED by: '{name}' (Due: {local_due_obj})")
                needs_lockdown = True
                break
        
        if not needs_lockdown:
            print("--> No incomplete homework due in this window. System unlocked.")

        self.is_locked = needs_lockdown
        self.write_config()
        
        if not self.is_paused:
            self.root.after(0, self.update_ui_state)

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
