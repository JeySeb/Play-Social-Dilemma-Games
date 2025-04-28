import tkinter as tk
from tkinter import messagebox
import subprocess

def run_experiment(port, agent_id):
    try:
        # Directly activate the environment and run the experiment without setting execution policy
        subprocess.Popen(["cmd", "/c", "..\\env\\Scripts\\activate && python client_with_communication.py --port {} --agent_id {}".format(port, agent_id)])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch experiment:\n{e}")

def on_submit():
    
    VM_NUMBER = 4
    
    map_choice = map_var.get()
    subgroup_choice = subgroup_var.get()

    if map_choice == "Commons Harvest Open":
        port, agent_id = 8084,  VM_NUMBER
    elif map_choice == "Commons Harvest Adversarial":
        if not subgroup_choice:
            messagebox.showwarning("Warning", "Please select a subgroup for Commons Harvest Adversarial.")
            return
        port = 8084 if subgroup_choice == "Subgroup 1" else 8085
        agent_id = (VM_NUMBER+1)%2 + 1
    elif map_choice in ["Coins", "Externality Mushrooms"]:
        port, agent_id = 8080 + VM_NUMBER, 1
    else:
        messagebox.showerror("Error", "Invalid map selection.")
        return

    if messagebox.askyesno("Confirmation", f"Start experiment with:\nPort: {port}\nAgent ID: {agent_id}?"):
        run_experiment(port, agent_id)

def update_subgroup_visibility():
    if map_var.get() == "Commons Harvest Adversarial":
        subgroup_frame.pack(pady=10)
    else:
        subgroup_frame.pack_forget()

# Create the main window
root = tk.Tk()
root.title("Experiment Selection")
root.geometry("450x400")
root.configure(bg='#2C2F33')

# Map selection
map_var = tk.StringVar(value="Commons Harvest Open")
tk.Label(root, text="Select the map assigned:", bg='#2C2F33', fg='white', font=("Arial", 12, "bold")).pack(pady=(20, 10))

maps = ["Commons Harvest Open", "Commons Harvest Adversarial", "Coins", "Externality Mushrooms"]
for map_name in maps:
    tk.Radiobutton(root, text=map_name, variable=map_var, value=map_name, bg='#2C2F33', fg='white',
                   selectcolor='#7289DA', font=("Arial", 11),
                   command=update_subgroup_visibility).pack(anchor=tk.W, padx=20)

# Subgroup selection (initially hidden)
subgroup_frame = tk.Frame(root, bg='#2C2F33')
tk.Label(subgroup_frame, text="Select your subgroup:", bg='#2C2F33', fg='white', font=("Arial", 12, "bold")).pack(pady=(10, 5))
subgroup_var = tk.StringVar()
tk.Radiobutton(subgroup_frame, text="Subgroup 1", variable=subgroup_var, value="Subgroup 1", bg='#2C2F33', fg='white',
               selectcolor='#7289DA', font=("Arial", 11)).pack(anchor=tk.W, padx=20)
tk.Radiobutton(subgroup_frame, text="Subgroup 2", variable=subgroup_var, value="Subgroup 2", bg='#2C2F33', fg='white',
               selectcolor='#7289DA', font=("Arial", 11)).pack(anchor=tk.W, padx=20)

# Submit button
submit_button = tk.Button(root, text="Start Experiment", command=on_submit,
                          bg='#7289DA', fg='white', font=("Arial", 12, "bold"), borderwidth=3)
submit_button.pack(pady=30)

# Initialize
update_subgroup_visibility()

# Run the application
root.mainloop()
