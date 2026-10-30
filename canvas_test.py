import requests
from datetime import datetime, timezone

# Set your specific domain and token
CANVAS_DOMAIN = "https://ohio.instructure.com/"
API_TOKEN = "24063~G9xAcyuXFexhGMaYHZQWnhEZYfU3Y3Kw9EW6kNnUyvByJvkM8mwRtM27ZUMNRJB2 "

url = f"{CANVAS_DOMAIN}/api/v1/users/self/todo"
headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    tasks = response.json()
    
    # Get the current date in your local system timezone
    today = datetime.now().astimezone().date()
    
    print(f"Homework Due Today ({today}):\n" + "="*30)
    
    if not tasks:
        print("No tasks found in Canvas.")
    
    found_due_today = False
    
    for item in tasks:
        if 'assignment' in item:
            name = item['assignment']['name']
            due_at_str = item['assignment']['due_at']
            
            if due_at_str:

                utc_due_obj = datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))

                local_due_obj = utc_due_obj.astimezone()
                local_due_date = local_due_obj.date()
                
                # Check if the assignment's due date matches today's date
                if local_due_date == today:
                    found_due_today = True
                    print(f"[ ] {name}")
                    print(f"    Due at: {local_due_obj.strftime('%I:%M %p')}\n")
    
    if not found_due_today and tasks:
        print("You have upcoming tasks, but nothing due today!")

else:
    print(f"Failed to connect. Status Code: {response.status_code}")