import tkinter as tk
from tkinter import ttk, messagebox
import threading
from automate_captcha import solve_captcha_and_submit

def start_solving():
    action = action_var.get()
    username = username_entry.get()
    email = email_entry.get()
    password = password_entry.get()

    # Run the solving process in a separate thread to avoid blocking the GUI
    threading.Thread(target=run_solver, args=(action, username, email, password), daemon=True).start()

def run_solver(action, username, email, password):
    try:
        if action == "Register":
            solve_captcha_and_submit(
                website_url='https://faucetpay.io/account/register',
                username=username,
                email=email,
                password=password,
                action=action
            )
        else:
            solve_captcha_and_submit(
                website_url='https://faucetpay.io/account/login',
                username=username,
                email=email,
                password=password,
                action=action
            )
        # Show success message in the main thread
        root.after(0, lambda: messagebox.showinfo("Success", "Form submitted successfully!"))
    except Exception as e:
        # Show error message in the main thread
        root.after(0, lambda: messagebox.showerror("Error", f"Failed to submit the form: {e}"))

def toggle_fields(event):
    action = action_var.get()
    if action == "Login":
        username_label.grid_remove()
        username_entry.grid_remove()
        confirm_password_label.grid_remove()
        confirm_password_entry.grid_remove()
    else:
        username_label.grid()
        username_entry.grid()
        confirm_password_label.grid()
        confirm_password_entry.grid()

def open_new_session():
    # Create a new top-level window
    new_window = tk.Toplevel(root)
    new_window.title("New CAPTCHA Solver Session")
    new_window.geometry("400x350")
    new_window.configure(bg="#f0f0f0")

    # Copy the layout from the main window
    action_var_new = tk.StringVar(value="Register")
    action_label_new = ttk.Label(new_window, text="Action:")
    action_label_new.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    action_dropdown_new = ttk.Combobox(new_window, textvariable=action_var_new, values=["Register", "Login"], state="readonly")
    action_dropdown_new.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    action_dropdown_new.bind("<<ComboboxSelected>>", lambda e: toggle_fields_new(e, new_window))

    username_label_new = ttk.Label(new_window, text="Username:")
    username_label_new.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    username_entry_new = ttk.Entry(new_window, width=40)
    username_entry_new.grid(row=2, column=1, padx=10, pady=5)

    ttk.Label(new_window, text="Email:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    email_entry_new = ttk.Entry(new_window, width=40)
    email_entry_new.grid(row=3, column=1, padx=10, pady=5)

    ttk.Label(new_window, text="Password:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
    password_entry_new = ttk.Entry(new_window, width=40, show="*")
    password_entry_new.grid(row=4, column=1, padx=10, pady=5)

    confirm_password_label_new = ttk.Label(new_window, text="Confirm Password:")
    confirm_password_label_new.grid(row=5, column=0, padx=10, pady=5, sticky="w")
    confirm_password_entry_new = ttk.Entry(new_window, width=40, show="*")
    confirm_password_entry_new.grid(row=5, column=1, padx=10, pady=5)

    solve_button_new = ttk.Button(new_window, text="Submit Form", command=lambda: start_solving_new(new_window))
    solve_button_new.grid(row=6, column=0, columnspan=2, pady=20)

    # Initial field visibility
    toggle_fields_new(None, new_window)

def toggle_fields_new(event, window):
    action = window.children['!combobox'].get()
    if action == "Login":
        window.children['!label2'].grid_remove()
        window.children['!entry'].grid_remove()
        window.children['!label4'].grid_remove()
        window.children['!entry3'].grid_remove()
    else:
        window.children['!label2'].grid()
        window.children['!entry'].grid()
        window.children['!label4'].grid()
        window.children['!entry3'].grid()

def start_solving_new(window):
    action = window.children['!combobox'].get()
    username = window.children['!entry'].get()
    email = window.children['!entry2'].get()
    password = window.children['!entry3'].get() if action == "Register" else window.children['!entry2'].get()

    # Run the solving process in a separate thread
    threading.Thread(target=run_solver, args=(action, username, email, password), daemon=True).start()

# Main window setup
root = tk.Tk()
root.title("CAPTCHA Solver")
root.geometry("400x350")
root.configure(bg="#f0f0f0")

# Style
style = ttk.Style()
style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 10))
style.configure("TButton", font=("Helvetica", 10))
style.configure("TCombobox", font=("Helvetica", 10))

# Action Selection
action_var = tk.StringVar(value="Register")
action_label = ttk.Label(root, text="Action:")
action_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
action_dropdown = ttk.Combobox(root, textvariable=action_var, values=["Register", "Login"], state="readonly")
action_dropdown.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
action_dropdown.bind("<<ComboboxSelected>>", toggle_fields)

# Username (for Register)
username_label = ttk.Label(root, text="Username:")
username_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
username_entry = ttk.Entry(root, width=40)
username_entry.grid(row=2, column=1, padx=10, pady=5)

# Email
ttk.Label(root, text="Email:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
email_entry = ttk.Entry(root, width=40)
email_entry.grid(row=3, column=1, padx=10, pady=5)

# Password
ttk.Label(root, text="Password:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
password_entry = ttk.Entry(root, width=40, show="*")
password_entry.grid(row=4, column=1, padx=10, pady=5)

# Confirm Password (for Register)
confirm_password_label = ttk.Label(root, text="Confirm Password:")
confirm_password_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
confirm_password_entry = ttk.Entry(root, width=40, show="*")
confirm_password_entry.grid(row=5, column=1, padx=10, pady=5)

# Submit Button
solve_button = ttk.Button(root, text="Submit Form", command=start_solving)
solve_button.grid(row=6, column=0, pady=20)

# New Session Button
new_session_button = ttk.Button(root, text="New Session", command=open_new_session)
new_session_button.grid(row=6, column=1, pady=20)

root.mainloop()