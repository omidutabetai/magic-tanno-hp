import tkinter as tk
from tkinter import messagebox, ttk

from . import fields
from .generic_editor import GenericEditor


class App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        master.title("マジックタンノ コンテンツ編集ツール")
        master.geometry("960x620")

        self.pack(fill="both", expand=True)
        self._build_menu()

        self.status_var = tk.StringVar(value="準備完了")
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken")
        status_bar.pack(side="bottom", fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.notebook = notebook

        self.editors: list[GenericEditor] = []
        for spec in (fields.MEMBERS_SPEC, fields.TIMELINE_SPEC, fields.WORKS_SPEC):
            editor = GenericEditor(notebook, spec, on_status=self._set_status)
            notebook.add(editor, text=spec.name)
            self.editors.append(editor)

        master.protocol("WM_DELETE_WINDOW", self._on_close)

        master.bind_all("<Control-z>", lambda e: self._undo_current())
        master.bind_all("<Control-y>", lambda e: self._redo_current())
        master.bind_all("<Control-Shift-Z>", lambda e: self._redo_current())

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="保存", command=self._save_current)
        file_menu.add_command(label="すべて保存", command=self._save_all)
        file_menu.add_command(label="再読み込み", command=self._reload_current)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self._on_close)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="元に戻す", accelerator="Ctrl+Z", command=self._undo_current)
        edit_menu.add_command(label="やり直す", accelerator="Ctrl+Y", command=self._redo_current)
        menubar.add_cascade(label="編集", menu=edit_menu)

        self.master.config(menu=menubar)

    def _current_editor(self) -> GenericEditor:
        return self.editors[self.notebook.index(self.notebook.select())]

    def _save_current(self) -> None:
        self._current_editor().save()

    def _save_all(self) -> None:
        for editor in self.editors:
            editor.save()
        self._set_status("すべて保存しました")

    def _reload_current(self) -> None:
        self._current_editor().reload()

    def _undo_current(self) -> None:
        self._current_editor().undo()

    def _redo_current(self) -> None:
        self._current_editor().redo()

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _on_close(self) -> None:
        if any(e.is_dirty() for e in self.editors):
            if not messagebox.askyesno("確認", "未保存の変更があります。保存せずに終了しますか？"):
                return
        self.master.destroy()


def run() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
