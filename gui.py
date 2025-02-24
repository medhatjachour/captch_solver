import tkinter as tk
from tkinter import ttk, messagebox
import threading
from automate_captcha import CaptchaSolver  # We only need CaptchaSolver now
import webbrowser
from selenium import webdriver

class CaptchaSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAPTCHA Solver")
        self.root.geometry("300x200")
        self.root.configure(bg="#f0f0f0")
        self.driver = None

        # Style configuration
        style = ttk.Style()
        style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TCombobox", font=("Helvetica", 10))

        # Action Selection
        self.action_var = tk.StringVar(value="Register")
        action_label = ttk.Label(root, text="Action:")
        action_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.action_dropdown = ttk.Combobox(root, textvariable=self.action_var, 
                                          values=["Register", "Login"], 
                                          state="readonly")
        self.action_dropdown.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # Open Website Button
        self.open_button = ttk.Button(root, text="Open Website", 
                                    command=self.open_website)
        self.open_button.grid(row=1, column=0, columnspan=2, pady=10)

        # Solve CAPTCHA Button
        self.solve_button = ttk.Button(root, text="Solve CAPTCHA", 
                                     command=self.start_solving)
        self.solve_button.grid(row=2, column=0, columnspan=2, pady=10)

        # Status Label
        self.status_label = ttk.Label(root, text="Ready")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5)

    def open_website(self):
        """Opens the website and initializes the browser"""
        if self.driver:
            self.driver.quit()  # Close any existing browser instance
        
        action = self.action_var.get()
        url = ("https://faucetpay.io/account/register" if action == "Register" 
               else "https://faucetpay.io/account/login")
        
        self.driver = webdriver.Chrome()
        self.driver.get(url)
        self.status_label.config(text=f"Opened {action} page")
        self.solve_button.config(state="normal")  # Ensure solve button is enabled

    def start_solving(self):
        """Starts the CAPTCHA solving process in a separate thread"""
        if not self.driver:
            messagebox.showwarning("Warning", "Please open the website first!")
            return

        self.status_label.config(text="Solving CAPTCHA...")
        self.solve_button.config(state="disabled")
        self.open_button.config(state="disabled")
        
        # Run solver in separate thread
        threading.Thread(target=self.run_solver, daemon=True).start()

    def run_solver(self):
        """Runs the CAPTCHA solver and updates GUI"""
        try:
            # Click the "I'm not a robot" checkbox
            # self.driver.find_element(tk.By.XPATH, "//div[span[text()=\"I'm not a robot\"]]").click()

            solver = CaptchaSolver(self.driver)
            
            # Attempt to solve slider CAPTCHA if present
            slider_solved = solver.solve_slider_captcha()
            if not slider_solved:
                raise Exception("Failed to solve slider CAPTCHA")
            
            # Attempt to solve icon CAPTCHA if present
            icon_solved = solver.solve_icon_captcha()
            if not icon_solved:
                raise Exception("Failed to solve icon CAPTCHA")

            # Update GUI from main thread
            self.root.after(0, lambda: [
                messagebox.showinfo("Success", "CAPTCHA solved successfully! Browser remains open."),
                self.status_label.config(text="CAPTCHA Solved"),
                self.solve_button.config(state="normal"),
                self.open_button.config(state="normal")
            ])
            
        except Exception as e:
            # Update GUI with error from main thread
            self.root.after(0, lambda: [
                messagebox.showerror("Error", f"Failed to solve CAPTCHA"),
                self.status_label.config(text="Error occurred"),
                self.solve_button.config(state="normal"),
                self.open_button.config(state="normal")
            ])
            print(e)

    def __del__(self):
        """Cleanup method to ensure browser closes when GUI is closed"""
        if self.driver:
            self.driver.quit()

def main():
    root = tk.Tk()
    app = CaptchaSolverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()