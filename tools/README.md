# magic-tanno-editor

`data/members.json` / `data/timeline.json` / `data/works.json` をGUIで編集するためのTkinterアプリ。

## 実行方法

```
cd tools
uv run python main.py
```

tkinterが動かない場合は、まず以下で切り分ける:

```
uv run python -c "import tkinter; tkinter.Tk()"
```
