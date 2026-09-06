from __future__ import annotations

import copy
import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Literal

from . import models

FieldType = Literal["text", "multiline", "list", "bool", "contacts"]

UNDO_STACK_LIMIT = 50


@dataclass
class FieldSpec:
    key: str
    label: str
    type: FieldType = "text"
    height: int = 4


@dataclass
class DataTypeSpec:
    name: str
    filename: str
    label_field: str
    fields: list[FieldSpec]


def _slugify(text: str, fallback_prefix: str) -> str:
    chars = [c.lower() if c.isalnum() and c.isascii() else "-" for c in text]
    slug = "".join(chars).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    if not slug:
        slug = f"{fallback_prefix}-{random.randint(1000, 9999)}"
    return slug


class ContactsEditor(ttk.Frame):
    """membersのcontacts配列（type/label/value/url）を編集する小さなサブエディタ。

    行をダブルクリックすると直接編集ダイアログが開く。何も選択していないときは
    「編集」「削除」ボタンをグレーアウトし、選択が必要なことを見た目で示す。
    """

    def __init__(self, master: tk.Widget, on_change: Callable[[], None]):
        super().__init__(master)
        self.on_change = on_change
        self.contacts: list[dict] = []

        self.listbox = tk.Listbox(self, height=4, exportselection=False)
        self.listbox.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.listbox.bind("<<ListboxSelect>>", self._update_button_states)
        self.listbox.bind("<Double-Button-1>", lambda e: self._edit())

        ttk.Button(self, text="追加", command=self._add).grid(row=1, column=0, sticky="ew")
        self.edit_btn = ttk.Button(self, text="編集", command=self._edit)
        self.edit_btn.grid(row=1, column=1, sticky="ew")
        self.delete_btn = ttk.Button(self, text="削除", command=self._delete)
        self.delete_btn.grid(row=1, column=2, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self._update_button_states()

    def set_contacts(self, contacts: list[dict]) -> None:
        self.contacts = [dict(c) for c in contacts]
        self._refresh()

    def get_contacts(self) -> list[dict]:
        return [dict(c) for c in self.contacts]

    def _refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for c in self.contacts:
            self.listbox.insert(tk.END, f"{c.get('label', '')}: {c.get('value', '')}")
        self._update_button_states()

    def _update_button_states(self, _event=None) -> None:
        state = "normal" if self.listbox.curselection() else "disabled"
        self.edit_btn.config(state=state)
        self.delete_btn.config(state=state)

    def _add(self) -> None:
        result = self._open_dialog()
        if result is not None:
            self.contacts.append(result)
            self._refresh()
            self.on_change()

    def _edit(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        result = self._open_dialog(self.contacts[idx])
        if result is not None:
            self.contacts[idx] = result
            self._refresh()
            self.on_change()

    def _delete(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if messagebox.askyesno("確認", "この連絡先を削除しますか？"):
            del self.contacts[idx]
            self._refresh()
            self.on_change()

    def _open_dialog(self, initial: dict | None = None) -> dict | None:
        dialog = tk.Toplevel(self)
        dialog.title("連絡先")
        dialog.transient(self)
        dialog.grab_set()

        vars_: dict[str, tk.StringVar] = {}
        for i, key in enumerate(("type", "label", "value", "url")):
            ttk.Label(dialog, text=key).grid(row=i, column=0, sticky="w", padx=4, pady=2)
            var = tk.StringVar(value=(initial or {}).get(key, ""))
            ttk.Entry(dialog, textvariable=var, width=40).grid(row=i, column=1, padx=4, pady=2)
            vars_[key] = var

        result: dict | None = None

        def on_ok() -> None:
            nonlocal result
            result = {k: v.get() for k, v in vars_.items()}
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        button_row = len(vars_)
        ttk.Button(dialog, text="OK", command=on_ok).grid(row=button_row, column=0, pady=6)
        ttk.Button(dialog, text="キャンセル", command=on_cancel).grid(row=button_row, column=1, pady=6)

        dialog.wait_window()
        return result


class GenericEditor(ttk.Frame):
    """1つのJSONファイル（オブジェクトの配列）を「一覧+詳細フォーム」で編集する汎用ウィジェット。

    入力内容はキー入力のたびに即座にメモリ上の self.data へ反映される（＝画面表示と
    self.data は常に一致する）。ディスクへの書き込みは保存ボタンを押したときだけ発生する。
    Ctrl+Z / Ctrl+Y は「選択中の項目を触り始める直前」「追加・削除・並び替えの直前」の
    スナップショットへ戻す/やり直す形の元に戻す機能（1文字単位の取り消しではない）。
    """

    def __init__(self, master: tk.Widget, spec: DataTypeSpec, on_status: Callable[[str], None]):
        super().__init__(master)
        self.spec = spec
        self.on_status = on_status
        self.data: list[dict] = []
        self.current_index: int | None = None
        self.dirty = False
        self.widgets: dict[str, tuple[str, object]] = {}

        self.undo_stack: list[list[dict]] = []
        self.redo_stack: list[list[dict]] = []
        self._pending_snapshot = True
        self._loading = False

        self._build_ui()
        self.reload(confirm=False)

    # --- UI construction ---------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 8))

        self.tree = ttk.Treeview(left, show="tree", selectmode="browse", height=20)
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="追加", command=self._add_entry).grid(row=0, column=0, sticky="ew")
        self.delete_btn = ttk.Button(btns, text="削除", command=self._delete_entry)
        self.delete_btn.grid(row=0, column=1, sticky="ew")
        self.up_btn = ttk.Button(btns, text="↑", command=lambda: self._move(-1))
        self.up_btn.grid(row=1, column=0, sticky="ew")
        self.down_btn = ttk.Button(btns, text="↓", command=lambda: self._move(1))
        self.down_btn.grid(row=1, column=1, sticky="ew")
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        self._update_list_buttons()

        right_container = ttk.Frame(self)
        right_container.grid(row=0, column=1, sticky="nsew")
        right_container.columnconfigure(0, weight=1)
        right_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(right_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_container, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for row, f in enumerate(self.spec.fields):
            ttk.Label(self.form, text=f.label).grid(row=row, column=0, sticky="nw", padx=4, pady=4)

            if f.key == "id":
                var = tk.StringVar()
                entry = ttk.Entry(self.form, textvariable=var, width=48)
                entry.grid(row=row, column=1, sticky="w", padx=4, pady=4)
                var.trace_add("write", lambda *_, k=f.key: self._on_field_change(k))
                ttk.Button(self.form, text="他項目から生成", command=self._generate_id).grid(
                    row=row, column=2, sticky="w", padx=4
                )
                self.widgets[f.key] = ("text", var)
                continue

            if f.type == "text" or f.type == "list":
                var = tk.StringVar()
                entry = ttk.Entry(self.form, textvariable=var, width=60)
                entry.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
                var.trace_add("write", lambda *_, k=f.key: self._on_field_change(k))
                self.widgets[f.key] = (f.type, var)
            elif f.type == "bool":
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(
                    self.form, variable=var, command=lambda k=f.key: self._on_field_change(k)
                )
                chk.grid(row=row, column=1, sticky="w", padx=4, pady=4)
                self.widgets[f.key] = ("bool", var)
            elif f.type == "multiline":
                text_widget = tk.Text(self.form, width=60, height=f.height, wrap="word")
                text_widget.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
                text_widget.bind("<KeyRelease>", lambda e, k=f.key: self._on_field_change(k))
                self.widgets[f.key] = ("multiline", text_widget)
            elif f.type == "contacts":
                sub = ContactsEditor(self.form, on_change=lambda k=f.key: self._on_field_change(k))
                sub.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
                self.widgets[f.key] = ("contacts", sub)

        self.form.columnconfigure(1, weight=1)

    # --- data <-> form -------------------------------------------------
    def _label_for(self, entry: dict) -> str:
        return str(entry.get(self.spec.label_field) or entry.get("id") or "(no title)")

    def _read_widget(self, kind: str, widget) -> object:
        if kind == "text":
            return widget.get()
        if kind == "list":
            items = [s.strip() for s in widget.get().split(",")]
            return [s for s in items if s]
        if kind == "bool":
            return bool(widget.get())
        if kind == "multiline":
            return widget.get("1.0", "end-1c")
        if kind == "contacts":
            return widget.get_contacts()
        raise ValueError(f"unknown field kind: {kind}")

    def _write_widget(self, kind: str, widget, value: object) -> None:
        if kind == "text":
            widget.set(value or "")
        elif kind == "list":
            widget.set(", ".join(value or []))
        elif kind == "bool":
            widget.set(bool(value))
        elif kind == "multiline":
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value or "")
        elif kind == "contacts":
            widget.set_contacts(value or [])

    def _load_entry_to_form(self, index: int | None) -> None:
        # プログラムからの値設定でも StringVar の trace/Text の入力イベントは発火しうるため、
        # ロード中は _on_field_change を素通りさせて誤ったUndoスナップショットや二重書き込みを防ぐ。
        self._loading = True
        try:
            entry = self.data[index] if index is not None else {}
            for key, (kind, widget) in self.widgets.items():
                self._write_widget(kind, widget, entry.get(key))
        finally:
            self._loading = False

    def _refresh_tree(self, select_index: int | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, entry in enumerate(self.data):
            self.tree.insert("", "end", iid=str(i), text=self._label_for(entry))
        if select_index is not None and 0 <= select_index < len(self.data):
            iid = str(select_index)
            self.tree.selection_set(iid)
            self.tree.see(iid)

    # --- event handlers --------------------------------------------------
    def _update_list_buttons(self) -> None:
        state = "normal" if self.current_index is not None else "disabled"
        self.delete_btn.config(state=state)
        self.up_btn.config(state=state)
        self.down_btn.config(state=state)

    def _on_field_change(self, key: str) -> None:
        if self._loading or self.current_index is None:
            return
        if self._pending_snapshot:
            self._capture_snapshot()
            self._pending_snapshot = False
        kind, widget = self.widgets[key]
        self.data[self.current_index][key] = self._read_widget(kind, widget)
        self.dirty = True
        if key == self.spec.label_field:
            self.tree.item(str(self.current_index), text=self._label_for(self.data[self.current_index]))

    def _generate_id(self) -> None:
        label_kind, label_widget = self.widgets.get(self.spec.label_field, (None, None))
        if label_kind in ("text", "list"):
            source = label_widget.get()
        elif label_kind == "multiline":
            source = label_widget.get("1.0", "end-1c")
        else:
            source = ""
        _, id_widget = self.widgets["id"]
        id_widget.set(_slugify(source, "item"))

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        new_index = int(sel[0]) if sel else None
        self.current_index = new_index
        self._load_entry_to_form(new_index)
        self._pending_snapshot = True
        self._update_list_buttons()

    def _add_entry(self) -> None:
        self._capture_snapshot()
        new_entry: dict = {}
        for f in self.spec.fields:
            if f.type == "list":
                new_entry[f.key] = []
            elif f.type == "bool":
                new_entry[f.key] = False
            elif f.type == "contacts":
                new_entry[f.key] = []
            else:
                new_entry[f.key] = ""
        new_entry["id"] = _slugify("new-item", "item")
        self.data.append(new_entry)
        self.dirty = True
        new_index = len(self.data) - 1
        self.current_index = new_index
        self._refresh_tree(select_index=new_index)
        self._load_entry_to_form(new_index)
        self._pending_snapshot = True
        self._update_list_buttons()

    def _delete_entry(self) -> None:
        if self.current_index is None:
            return
        if not messagebox.askyesno("確認", "選択中の項目を削除しますか？"):
            return
        self._capture_snapshot()
        del self.data[self.current_index]
        self.dirty = True
        self.current_index = None
        self._refresh_tree()
        self._load_entry_to_form(None)
        self._pending_snapshot = True
        self._update_list_buttons()

    def _move(self, offset: int) -> None:
        if self.current_index is None:
            return
        i = self.current_index
        j = i + offset
        if not (0 <= j < len(self.data)):
            return
        self._capture_snapshot()
        self.data[i], self.data[j] = self.data[j], self.data[i]
        self.dirty = True
        self.current_index = j
        self._refresh_tree(select_index=j)
        self._load_entry_to_form(j)
        self._pending_snapshot = True

    # --- undo / redo ---------------------------------------------------
    def _capture_snapshot(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.data))
        self.redo_stack.clear()
        if len(self.undo_stack) > UNDO_STACK_LIMIT:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if not self.undo_stack:
            self.on_status(f"{self.spec.name}: これ以上元に戻せません")
            return
        self.redo_stack.append(copy.deepcopy(self.data))
        self.data = self.undo_stack.pop()
        self._pending_snapshot = True
        self._after_history_change()
        self.on_status(f"{self.spec.name}: 元に戻しました")

    def redo(self) -> None:
        if not self.redo_stack:
            self.on_status(f"{self.spec.name}: やり直せる操作がありません")
            return
        self.undo_stack.append(copy.deepcopy(self.data))
        self.data = self.redo_stack.pop()
        self._pending_snapshot = True
        self._after_history_change()
        self.on_status(f"{self.spec.name}: やり直しました")

    def _after_history_change(self) -> None:
        if self.current_index is not None and self.current_index >= len(self.data):
            self.current_index = len(self.data) - 1 if self.data else None
        self._refresh_tree(select_index=self.current_index)
        self._load_entry_to_form(self.current_index)
        self.dirty = True
        self._update_list_buttons()

    # --- persistence -------------------------------------------------------
    def is_dirty(self) -> bool:
        return self.dirty

    def save(self) -> None:
        models.save_json(self.spec.filename, self.data)
        self.dirty = False
        self.on_status(f"{self.spec.name}: 保存しました（{self.spec.filename}）")

    def reload(self, confirm: bool = True) -> None:
        if confirm and self.dirty:
            if not messagebox.askyesno("確認", "未保存の変更は破棄されます。再読み込みしますか？"):
                return
        self.data = models.load_json(self.spec.filename)
        self.current_index = None
        self.dirty = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._pending_snapshot = True
        self._refresh_tree()
        self._load_entry_to_form(None)
        self._update_list_buttons()
        self.on_status(f"{self.spec.name}: 読み込みました（{self.spec.filename}）")
