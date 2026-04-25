_BLOCK_TYPES = {
    "paragraph", "bulletList", "listItem", "heading",
    "blockquote", "codeBlock", "orderedList",
}


def parse_adf(adf_json: object) -> str:
    if not isinstance(adf_json, dict):
        return ""
    return _traverse(adf_json).strip()


def _traverse(node: dict) -> str:
    node_type = node.get("type", "")
    if node_type == "text":
        return node.get("text", "")

    children = node.get("content") or []
    parts = [_traverse(child) for child in children if isinstance(child, dict)]

    if node_type in _BLOCK_TYPES:
        return "\n".join(p for p in parts if p)
    return "".join(parts)
