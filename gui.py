import tkinter as tk
from tkinter import messagebox
from automate_captcha import solve_captcha_and_submit  # Import the automation function

def start_solving():
    website_url = website_entry.get()
    username = username_entry.get()
    email = email_entry.get()
    password = password_entry.get()
    confirm_password = confirm_password_entry.get()

    if password != confirm_password:
        messagebox.showerror("Error", "Passwords do not match!")
        return

    try:
        # Call the automation function with the inputs
        solve_captcha_and_submit(website_url, username, email, password)
        messagebox.showinfo("Success", "Form submitted successfully!")
    except Exception as e:
        print("Error", f"Failed to submit the form: {e}")
        messagebox.showerror("Error", f"Failed to submit the form: {e}")

# Create the main window
root = tk.Tk()
root.title("CAPTCHA Solver")

# Add input fields
tk.Label(root, text="Website URL:").grid(row=0, column=0, padx=10, pady=5)
website_entry = tk.Entry(root, width=40)
website_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Username:").grid(row=1, column=0, padx=10, pady=5)
username_entry = tk.Entry(root, width=40)
username_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Email:").grid(row=2, column=0, padx=10, pady=5)
email_entry = tk.Entry(root, width=40)
email_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Password:").grid(row=3, column=0, padx=10, pady=5)
password_entry = tk.Entry(root, width=40, show="*")
password_entry.grid(row=3, column=1, padx=10, pady=5)

tk.Label(root, text="Confirm Password:").grid(row=4, column=0, padx=10, pady=5)
confirm_password_entry = tk.Entry(root, width=40, show="*")
confirm_password_entry.grid(row=4, column=1, padx=10, pady=5)

# Add a button to trigger CAPTCHA solving and form submission
solve_button = tk.Button(root, text="Submit Form", command=start_solving)
solve_button.grid(row=5, column=0, columnspan=2, pady=20)

# Run the application
root.mainloop()