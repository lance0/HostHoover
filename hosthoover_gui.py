# hosthoover_gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
import threading

from hosthoover import run_hosthoover

class HostHooverUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HostHoover Backup Tool")
        self.geometry("420x400")
        self.create_widgets()

    def create_widgets(self):
        labels = [
            ("Subnet (CIDR):", 'subnet'),
            ("Username:", 'username'),
            ("Password:", 'password'),
            ("SSH Key Path:", 'ssh_key'),
            ("Device Type:", 'device_type'),
            ("Output Directory:", 'output_dir'),
            ("Archive Format (zip/7z/rar):", 'archive_format')
        ]
        self.entries = {}

        for i, (label, key) in enumerate(labels):
            tk.Label(self, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(self, width=30)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[key] = entry

        self.entries['password'].config(show='*')

        tk.Button(self, text="Browse SSH Key", command=self.browse_ssh_key).grid(row=3, column=2, padx=5)
        tk.Button(self, text="Browse Output Dir", command=self.browse_output_dir).grid(row=5, column=2, padx=5)
        tk.Button(self, text="Run Backup", command=self.run_backup_thread).grid(row=8, column=0, columnspan=3, pady=20)

    def browse_ssh_key(self):
        path = filedialog.askopenfilename(title="Select SSH Key")
        if path:
            self.entries['ssh_key'].delete(0, tk.END)
            self.entries['ssh_key'].insert(0, path)

    def browse_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.entries['output_dir'].delete(0, tk.END)
            self.entries['output_dir'].insert(0, path)

    def run_backup_thread(self):
        # Run backup in a thread to keep UI responsive
        threading.Thread(target=self.run_backup, daemon=True).start()

    def run_backup(self):
        config = {k: e.get() for k, e in self.entries.items()}
        # Set defaults
        config['archive_format'] = config.get('archive_format') or 'zip'
        config['device_type'] = config.get('device_type') or 'cisco_ios'
        config['output_dir'] = config.get('output_dir') or 'backups'
        # Validation
        if not config['subnet'] or not config['username']:
            messagebox.showerror("Error", "Subnet and Username are required.")
            return
        if not config['password'] and not config['ssh_key']:
            messagebox.showerror("Error", "Password or SSH Key Path is required.")
            return
        try:
            results, archive_path = run_hosthoover(config)
            msg = (
                f"Backup complete!\n"
                f"Successful: {results.get('success', 0)}\n"
                f"Failed: {results.get('failed', 0)}\n"
                f"Write Errors: {results.get('write_error', 0)}\n"
                f"Archive: {archive_path}"
            )
            messagebox.showinfo("HostHoover", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == '__main__':
    app = HostHooverUI()
    app.mainloop()
