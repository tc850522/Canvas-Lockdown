import tkinter as tk
import requests
import threading
import time
import json
from datetime import datetime, timedelta

class CanvasLockdownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Canvas Homework Enforcer")
        self.root.geometry("400x450")
        
        # State variables
        self.is_locked = False
        self.pause_until = 0
        self.running = True
        
        self.build_gui()
        
        # Start background API polling thread
        self.api_thread = threading.Thread(target=self.poll_canvas_api, daemon=True)
        self.api_thread.start()

    def build_gui(self):
        tk.Label(self.root, text="Canvas Domain (e.g., https://canvas.edu):").pack(pady=5)
        self.domain_entry = tk.Entry(self.root, width=40)
        self.domain_entry.pack()

        tk.Label(self.root, text="API Access Token:").pack(pady=5)
        self.token_entry = tk.Entry(self.root, width=40, show="*")
        self.token_entry.pack()

        tk.Label(self.root, text="Lockdown if due within (Days):").pack(pady=5)
        self.days_entry = tk.Entry(self.root, width=10)
        self.days_entry.insert(0, "0") 
        self.days_entry.pack()

        self.status_label = tk.Label(self.root, text="Status: Unlocked", fg="green", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=20)

        self.pause_btn = tk.Button(self.root, text="Pause Lockdown (1 Hour)", command=self.pause_lockdown, state=tk.DISABLED)
        self.pause_btn.pack(pady=10)

    def pause_lockdown(self):
        if self.is_locked and time.time() > self.pause_until:
            # Add 3,600 seconds (1 hour) to current time
            self.pause_until = int(time.time()) + 3600
            self.status_label.config(text="Status: PAUSED (1 Hour)", fg="orange")
            self.pause_btn.config(state=tk.DISABLED)
            self.write_config()
            self.root.after(3600000, self.update_ui_state) # 3,600,000 milliseconds[cite: 2]

    def write_config(self):
        """Writes the current state to a shared JSON file for the C++ Enforcer[cite: 4]."""
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
        """Background loop to check Canvas API every 60 seconds[cite: 2]."""
        while self.running:
            domain = self.domain_entry.get().strip()
            token = self.token_entry.get().strip()
            days_in_advance = self.days_entry.get().strip()
            
            if domain and token and days_in_advance.isdigit():
                url = f"{domain}/api/v1/users/self/todo" # Polling the todo endpoint[cite: 4]
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
        # Get the current date in local system timezone[cite: 2, 5]
        today = datetime.now().astimezone().date()
        target_date = today + timedelta(days=days_in_advance)
        
        needs_lockdown = False
        
        for item in tasks:
            if 'assignment' in item and item['assignment']['due_at']:
                due_at_str = item['assignment']['due_at']
                
                # Convert the Canvas UTC string to local timezone[cite: 2, 5]
                utc_due_obj = datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
                local_due_date = utc_due_obj.astimezone().date()
                
                if local_due_date <= target_date:
                    needs_lockdown = True
                    break
        
        self.is_locked = needs_lockdown
        self.write_config()
        self.update_ui_state()

    def update_ui_state(self):
        if time.time() < self.pause_until:
            self.status_label.config(text="Status: PAUSED", fg="orange")
            self.pause_btn.config(state=tk.DISABLED)
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