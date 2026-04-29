from app.services.chat_engine import _normalize_taxonomy_text


def test_normalize_taxonomy_text_dedupes_repeated_hierarchy_labels():
    assert _normalize_taxonomy_text("综合、综合、综合Ⅲ") == "综合Ⅲ"
    assert _normalize_taxonomy_text("算力租赁、东数西算(算力)、数据中心、AI应用") == "算力租赁、东数西算(算力)、数据中心、AI应用"
