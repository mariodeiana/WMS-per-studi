from __future__ import annotations

from html import escape

from backend.wms_core.models import Evidence, Practice, Task


STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f7fb;color:#172033}header{background:#16324f;color:white;padding:1rem 2rem}main{max-width:1100px;margin:2rem auto;padding:0 1rem}.card{background:white;border-radius:10px;padding:1.25rem;margin-bottom:1rem;box-shadow:0 2px 8px #ccd5e1}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}.instructions{border-left:5px solid #2878c8;background:#eef7ff;padding:1rem}.evidence,.audit{padding:.55rem;border-bottom:1px solid #dde5ef}label{display:block;font-weight:600;margin-top:.75rem}input,textarea,select{box-sizing:border-box;width:100%;padding:.65rem;border:1px solid #aab7c5;border-radius:5px}button,.button{display:inline-block;background:#1769aa;color:#fff;border:0;border-radius:5px;padding:.7rem 1rem;margin-top:1rem;text-decoration:none}.danger{background:#9f2d2d}.muted{color:#607086}.pill{background:#e1ebf5;border-radius:20px;padding:.25rem .6rem}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:.7rem;border-bottom:1px solid #dde5ef}
"""


def page(title: str, content: str) -> str:
    return f"<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{escape(title)}</title><style>{STYLE}</style></head><body><header><strong>WMS per studi · v0.3</strong></header><main><h1>{escape(title)}</h1>{content}</main></body></html>"


def evidence_list(items: list[Evidence]) -> str:
    if not items:
        return "<p class='muted'>Nessuna evidenza.</p>"
    return "".join(
        f"<div class='evidence'><strong>{escape(item.name)}</strong> · {escape(item.origin.value)} · {escape(item.author)}<br><span class='muted'>{escape(item.content_ref or 'contenuto demo')}</span></div>"
        for item in items
    )


def result_fields(action: str, button: str) -> str:
    return f"""<form method='post' action='{escape(action)}'>
<label for='outcome'>Outcome / esito</label><input id='outcome' name='outcome' required>
<label for='note'>Nota</label><textarea id='note' name='note' rows='4'></textarea>
<fieldset><legend>Allegati / evidenze</legend>
<label for='evidence_name'>Nome o titolo</label><input id='evidence_name' name='evidence_name' placeholder='es. ricevuta.pdf'>
<label for='evidence_ref'>Riferimento al contenuto</label><input id='evidence_ref' name='evidence_ref' placeholder='es. file://ricevuta.pdf'>
<label for='evidence_name_2'>Seconda evidenza (opzionale)</label><input id='evidence_name_2' name='evidence_name' placeholder='es. prospetto.csv'>
<label for='evidence_ref_2'>Secondo riferimento</label><input id='evidence_ref_2' name='evidence_ref' placeholder='es. file://prospetto.csv'>
<p class='muted'>API: i campi evidence_name ed evidence_ref sono ripetibili senza limite.</p></fieldset>
<button type='submit'>{escape(button)}</button></form>"""


def task_row(practice: Practice, task: Task, manager: bool = False) -> str:
    result = task.result
    evidence = evidence_list(result.attachments) if result else "<span class='muted'>—</span>"
    reopen = ""
    if manager and result:
        reopen = f"<form method='post' action='/practices/{escape(practice.id)}/tasks/{escape(task.code)}/reopen'><button class='danger'>Riapri task</button></form>"
    return f"<tr><td>{escape(task.code)}<br>{escape(task.title)}</td><td>{escape(task.assigned_to or '—')}</td><td>{escape(task.status.value)}</td><td>{escape(task.completed_by or '—')}</td><td>{escape(result.outcome if result else '—')}<br>{escape(result.note if result else '')}</td><td>{evidence}{reopen}</td></tr>"
