import customtkinter as ctk
import sqlite3
import threading
from datetime import datetime, timedelta
from plyer import notification
from tkinter import messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

conn = sqlite3.connect("task_app.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        deadline TEXT,
        completed INTEGER DEFAULT 0
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT
    )
""")
conn.commit()

notif_log = []

def export_notite_pdf():
    filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not filepath:
        return

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Exported Notes:")
    y -= 30

    cursor.execute("SELECT title, content FROM notes")
    notite = cursor.fetchall()

    for title, content in notite:
        c.drawString(50, y, f"Title: {title}")
        y -= 20
        lines = content.split('\n')
        for line in lines:
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
            c.drawString(70, y, line)
            y -= 20
        y -= 10

    c.save()
    messagebox.showinfo("Export PDF", f"Notes successfully exported to:\n{filepath}")

def get_upcoming_tasks():
    now = datetime.now()
    limit = now + timedelta(minutes=1)
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND deadline <= ?", (limit.strftime("%Y-%m-%d %H:%M"),))
    return cursor.fetchall()

def check():
    while True:
        now = datetime.now().date()
        cursor.execute("SELECT id, title, deadline, completed FROM tasks WHERE completed = 0")
        tasks = cursor.fetchall()
        for task in tasks:
            try:
                deadline_date = datetime.strptime(task[2], "%Y-%m-%d %H:%M").date()
                if deadline_date < now:
                    message = f"{task[1]} - expired on {task[2]}"
                elif deadline_date == now:
                    message = f"{task[1]} - due today ({task[2]})"
                else:
                    continue
                notification.notify(title="Task Alert", message=message, timeout=5)
                notif_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                if len(notif_log) > 5:
                    notif_log.pop(0)
            except:
                continue
        threading.Event().wait(60)
        
class PaginaPrincipala(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Task & Notes Manager", font=("Arial", 24)).pack(pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.search_taskuri)
        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search tasks...")
        self.search_entry.pack(pady=5)
        ctk.CTkButton(self, text="Completed Tasks", command=self.afiseaza_taskuri_finalizate).pack(pady=2)
        ctk.CTkButton(self, text="Pending Tasks", command=self.afiseaza_taskuri_nefinalizate).pack(pady=2)
        self.task_listbox = ctk.CTkTextbox(self, width=500, height=200)
        self.task_listbox.pack(pady=10)

        ctk.CTkButton(self, text="Task Editor", command=lambda: controller.show_frame(EditorTaskuri)).pack(pady=5)
        ctk.CTkButton(self, text="Notes Editor", command=lambda: controller.show_frame(EditorNotite)).pack(pady=5)

        ctk.CTkLabel(self, text="Latest Notifications:").pack(pady=(10, 0))
        self.notif_logbox = ctk.CTkTextbox(self, width=500, height=100)
        self.notif_logbox.pack(pady=5)
        self.afiseaza_taskuri()

    def afiseaza_taskuri(self):
        self.task_listbox.delete("1.0", ctk.END)
        today = datetime.now().date()
        cursor.execute("SELECT title, deadline, completed FROM tasks")
        self.taskuri = cursor.fetchall()
        for title, deadline, completed in self.taskuri:
            try:
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d %H:%M").date()
                if not completed and deadline_date < today:
                    status = "⚠️"
                else:
                    status = "✔️" if completed else "❌"
            except:
                status = "❌"
            self.task_listbox.insert(ctk.END, f"{status} {title} - {deadline}\n")
        self.refresh_notif_log()

    def afiseaza_taskuri_finalizate(self):
        self.task_listbox.delete("1.0", ctk.END)
        cursor.execute("SELECT title, deadline FROM tasks WHERE completed = 1")
        for title, deadline in cursor.fetchall():
            self.task_listbox.insert(ctk.END, f"✔️ {title} - {deadline}\n")

    def afiseaza_taskuri_nefinalizate(self):
        self.task_listbox.delete("1.0", ctk.END)
        cursor.execute("SELECT title, deadline FROM tasks WHERE completed = 0")
        for title, deadline in cursor.fetchall():
            self.task_listbox.insert(ctk.END, f"❌ {title} - {deadline}\n")

    def search_taskuri(self, *args):
        query = self.search_var.get().lower()
        self.task_listbox.delete("1.0", ctk.END)
        for title, deadline, completed in self.taskuri:
            if query in title.lower():
                status = "✔️" if completed else "❌"
                self.task_listbox.insert(ctk.END, f"{status} {title} - {deadline}\n")

    def refresh_notif_log(self):
        self.notif_logbox.delete("1.0", ctk.END)
        for msg in notif_log:
            self.notif_logbox.insert(ctk.END, msg + "\n")

class EditorTaskuri(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        self.controller = controller

        self.entry_title = ctk.CTkEntry(self, placeholder_text="Title")
        self.entry_title.pack(pady=5)
        
        self.entry_deadline = ctk.CTkEntry(self, placeholder_text="Deadline (YYYY-MM-DD HH:MM)")
        self.entry_deadline.pack(pady=5)

        ctk.CTkButton(self, text="Add Task", command=self.adauga_task).pack(pady=5)
        ctk.CTkButton(self, text="Back", command=lambda: controller.show_frame(PaginaPrincipala)).pack(pady=5)

        self.lista = ctk.CTkFrame(self)
        self.lista.pack(pady=5)

        self.refresh_taskuri()

    def adauga_task(self):
        titlu = self.entry_title.get()
        deadline = self.entry_deadline.get()
        try:
            datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("Eroare", "Formatul datei trebuie să fie YYYY-MM-DD HH:MM")
            return
        if titlu:
            cursor.execute("INSERT INTO tasks (title,  deadline) VALUES (?, ?)", 
                           (titlu, deadline))
            conn.commit()
            self.refresh_taskuri()
            self.entry_title.delete(0, ctk.END)
            self.entry_deadline.delete(0, ctk.END)

    def sterge_task(self, id):
        cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()
        self.refresh_taskuri()

    def marcheaza_completat(self, id):
        cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (id,))
        conn.commit()
        self.refresh_taskuri()

    def refresh_taskuri(self):
        for widget in self.lista.winfo_children():
            widget.destroy()

        cursor.execute("SELECT * FROM tasks")
        tasks = cursor.fetchall()

        for task in tasks:
            frame = ctk.CTkFrame(self.lista)
            frame.pack(fill="x", pady=2, padx=2)

            titlu = task[1] + (" ✅" if task[3] else "")
            text = f"{titlu}\nDeadline: {task[2] or 'Nespecificat'}"
            

            lbl = ctk.CTkLabel(frame, text=text, justify="left")
            lbl.pack(side="left", padx=5)

            if not task[3]:
                btn_done = ctk.CTkButton(frame, text="✔", width=40, command=lambda i=task[0]: self.marcheaza_completat(i))
                btn_done.pack(side="right", padx=2)

            btn_del = ctk.CTkButton(frame, text="🗑", width=40, command=lambda i=task[0]: self.sterge_task(i))
            btn_del.pack(side="right", padx=2)
    def update_task_status(self, task_id, status):
        cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (status, task_id))
        conn.commit()
        self.refresh_taskuri()
    
        
class EditorNotite(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.entry_title = ctk.CTkEntry(self, placeholder_text="Note Title")
        self.entry_title.pack(pady=5)

        self.entry = ctk.CTkTextbox(self, width=600, height=100)
        self.entry.pack(pady=5)

        ctk.CTkButton(self, text="Add Note", command=self.adauga_notita).pack(pady=5)
        ctk.CTkButton(self, text="Export to PDF", command=export_notite_pdf).pack(pady=5)
        ctk.CTkButton(self, text="Back", command=lambda: controller.show_frame(PaginaPrincipala)).pack(pady=5)

        self.lista = ctk.CTkScrollableFrame(self)
        self.lista.pack(fill="both", expand=True, pady=10)

        self.refresh_notite()

    def adauga_notita(self):
        titlu = self.entry_title.get().strip()
        continut = self.entry.get("1.0", ctk.END).strip()
        if titlu and continut:
            cursor.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (titlu, continut))
            conn.commit()
            self.refresh_notite()
            self.entry.delete("1.0", ctk.END)
            self.entry_title.delete(0, ctk.END)
        else:
            messagebox.showwarning("Warning", "Please fill in both title and content.")

    def refresh_notite(self):
        for widget in self.lista.winfo_children():
            widget.destroy()

        cursor.execute("SELECT * FROM notes")
        notes = cursor.fetchall()

        for note in notes:
            frame = ctk.CTkFrame(self.lista)
            frame.pack(fill="x", pady=2, padx=2)

            title_label = ctk.CTkLabel(frame, text=f"{note[1]}", font=("Arial", 14, "bold"))
            title_label.pack(anchor="w", padx=5)

            content_text = ctk.CTkTextbox(frame, height=60, wrap="word")
            content_text.insert("1.0", note[2])
            content_text.pack(fill="x", padx=5)

            ctk.CTkButton(frame, text="💾 Save", width=50, command=lambda i=note[0], t=content_text: self.update_notita(i, t.get("1.0", ctk.END).strip())).pack(side="left", padx=5)
            ctk.CTkButton(frame, text="🗑", width=40, command=lambda i=note[0]: self.sterge_notita(i)).pack(side="right", padx=5)

    def sterge_notita(self, id):
        cursor.execute("DELETE FROM notes WHERE id = ?", (id,))
        conn.commit()
        self.refresh_notite()

    def update_notita(self, id, continut):
        cursor.execute("UPDATE notes SET content = ? WHERE id = ?", (continut, id))
        conn.commit()
        self.refresh_notite()
class Aplicatie(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Task & Notes Manager")
        self.geometry("600x600")

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        self.frames = {}
        for F in (PaginaPrincipala, EditorTaskuri, EditorNotite):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(PaginaPrincipala)

    def show_frame(self, page):
        frame = self.frames[page]
        if hasattr(frame, 'afiseaza_taskuri'):
            frame.afiseaza_taskuri()
        frame.tkraise()

if __name__ == "__main__":
    threading.Thread(target=check, daemon=True).start()
    app = Aplicatie()
    app.mainloop()
 