import tkinter as tk
from tkinter import ttk, messagebox
from automate_captcha import solve_captcha_and_submit

def start_solving():
    action = action_var.get()
    website_url = website_entry.get()
    email = email_entry.get()
    password = password_entry.get()



    try:
        if action == "Register":
            solve_captcha_and_submit(website_url='https://faucetpay.io/account/register', username="adasdaasd", email="asdasdasd@adsdas.asd", password="asdasd123asd!@")
        else:
            solve_captcha_and_submit(website_url='https://faucetpay.io/account/login', email="adasdasd@adsdas.asd", password="asdasasd@!asda213d")
        messagebox.showinfo("Success", "Form submitted successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to submit the form: {e}")

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

root = tk.Tk()
root.title("CAPTCHA Solver")
root.geometry("400x350")
root.configure(bg="#f0f0f0")

# Style
style = ttk.Style()
style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 10))
style.configure("TButton", font=("Helvetica", 10), background="#4CAF50", foreground="white")
style.configure("TCombobox", font=("Helvetica", 10))

# Action Selection
action_var = tk.StringVar(value="Register")
action_label = ttk.Label(root, text="Action:")
action_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
action_dropdown = ttk.Combobox(root, textvariable=action_var, values=["Register", "Login"], state="readonly")
action_dropdown.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
action_dropdown.bind("<<ComboboxSelected>>", toggle_fields)

# Website URL
ttk.Label(root, text="Website URL:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
website_entry = ttk.Entry(root, width=40)
website_entry.grid(row=1, column=1, padx=10, pady=5)

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
solve_button.grid(row=6, column=0, columnspan=2, pady=20)

root.mainloop()