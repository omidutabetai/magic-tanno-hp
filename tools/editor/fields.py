from .generic_editor import DataTypeSpec, FieldSpec

MEMBERS_SPEC = DataTypeSpec(
    name="構成員",
    filename="members.json",
    label_field="name",
    fields=[
        FieldSpec("id", "ID"),
        FieldSpec("name", "名前"),
        FieldSpec("roles", "役割（カンマ区切り）", type="list"),
        FieldSpec("description", "説明", type="multiline", height=5),
        FieldSpec("contacts", "連絡先", type="contacts"),
    ],
)

TIMELINE_SPEC = DataTypeSpec(
    name="年表",
    filename="timeline.json",
    label_field="title",
    fields=[
        FieldSpec("id", "ID"),
        FieldSpec("datetime", "日付（YYYY-MM-DD）"),
        FieldSpec("displayDate", "表示用日付"),
        FieldSpec("title", "タイトル"),
        FieldSpec("description", "説明", type="multiline", height=5),
    ],
)

WORKS_SPEC = DataTypeSpec(
    name="頒布物",
    filename="works.json",
    label_field="title",
    fields=[
        FieldSpec("id", "ID"),
        FieldSpec("type", "種別（新刊 / 既刊 / 既刊（電子）等）"),
        FieldSpec("event", "頒布イベント（不明なら空欄）"),
        FieldSpec("author", "著者 / シリーズ名"),
        FieldSpec("title", "タイトル"),
        FieldSpec("description", "説明", type="multiline", height=5),
        FieldSpec("url", "URL（不明なら空欄）"),
    ],
)
