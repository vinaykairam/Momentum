from __future__ import annotations

from html import escape

from app.schemas.focus import FocusRecommendation

EINK_STYLES = """
:root {
  color-scheme: light;
  --background: #fafafa;
  --foreground: #0a0a0a;
  --muted: #737373;
  --border: rgba(0, 0, 0, 0.12);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--background);
  color: var(--foreground);
  font-family: "SF Pro Display", "Inter", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

main {
  max-width: 42rem;
  margin: 0 auto;
  padding: 3rem 1.5rem 4rem;
}

h1 {
  margin: 0 0 3.5rem;
  font-size: 1.875rem;
  font-weight: 400;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.empty-state {
  padding: 4rem 0;
  text-align: center;
  font-size: 1.25rem;
  color: var(--muted);
}

.stream-divider {
  height: 1px;
  margin: 2rem 1rem;
  border: none;
  background: var(--border);
}

.stream-group {
  padding: 1.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 1.25rem;
  background: rgba(0, 0, 0, 0.02);
}

.stream-group-title {
  margin: 0 0 1.25rem;
  padding: 0 0.5rem;
  font-size: 1rem;
  font-weight: 400;
  color: var(--muted);
  letter-spacing: 0.02em;
}

.stream-group-items .focus-item + .focus-item {
  border-top: 1px solid var(--border);
}

.stream-group-items .focus-item:first-child {
  padding-top: 1.25rem;
}

.focus-item {
  display: block;
  padding: 0.25rem 0.5rem 1rem;
}

.stream-group-items .focus-item {
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

.focus-stream {
  display: block;
  font-size: 1rem;
  color: var(--muted);
}

.focus-action {
  display: block;
  margin-top: 0.375rem;
  font-size: 1.25rem;
  line-height: 1.5;
  letter-spacing: -0.015em;
}
"""


def format_stream_label(stream_name: str, parent_stream_name: str | None) -> str:
    if parent_stream_name:
        return f"{parent_stream_name} · {stream_name}"
    return stream_name


def group_focus_recommendations(
    focus: list[FocusRecommendation],
) -> list[tuple[str | None, list[FocusRecommendation], bool]]:
    groups: list[list] = []
    parent_index: dict[str, int] = {}

    for item in focus:
        if item.parent_stream_name:
            parent = item.parent_stream_name
            index = parent_index.get(parent)
            if index is None:
                parent_index[parent] = len(groups)
                groups.append([parent, [item], True])
            else:
                groups[index][1].append(item)
        else:
            groups.append([None, [item], False])

    return [(parent, items, grouped) for parent, items, grouped in groups]


def render_focus_item(item: FocusRecommendation, *, nested: bool) -> str:
    stream_label = (
        escape(item.stream_name)
        if nested
        else escape(format_stream_label(item.stream_name, item.parent_stream_name))
    )
    action = escape(item.action)
    return (
        f'<article class="focus-item">'
        f'<span class="focus-stream">{stream_label}</span>'
        f'<span class="focus-action">{action}</span>'
        f"</article>"
    )


def render_today_page(focus: list[FocusRecommendation]) -> str:
    if not focus:
        body = '<p class="empty-state">Nothing queued for today.</p>'
    else:
        sections: list[str] = []
        groups = group_focus_recommendations(focus)
        for index, (parent_name, items, is_grouped) in enumerate(groups):
            if index > 0:
                sections.append('<hr class="stream-divider" aria-hidden="true">')

            item_html = "".join(render_focus_item(item, nested=is_grouped) for item in items)
            if is_grouped and parent_name:
                sections.append(
                    f'<section class="stream-group">'
                    f'<p class="stream-group-title">{escape(parent_name)}</p>'
                    f'<div class="stream-group-items">{item_html}</div>'
                    f"</section>"
                )
            else:
                sections.append(f'<section>{item_html}</section>')

        body = "".join(sections)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="light" />
    <title>Today · Momentum</title>
    <style>{EINK_STYLES}</style>
  </head>
  <body>
    <main>
      <h1>Today</h1>
      {body}
    </main>
  </body>
</html>
"""
