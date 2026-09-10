# files/web/sections/docs.py
"""
Секция документации — отображение MD файлов из files/docs/
"""
import re
from pathlib import Path
from flask import render_template_string, jsonify
from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('docs')

this_section_in_control_panel = True
section_icon = "bi-book"
section_name = "Документация"
section_order = 6


def t(key, **kwargs):
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


def _md_to_html(md_text):
    """Простой конвертер MD → HTML"""
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Блоки кода
        if stripped.startswith('```'):
            if in_code_block:
                html_lines.append('</code></pre>')
                in_code_block = False
            else:
                lang = stripped[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # Пустая строка
        if not stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('')
            continue

        # Заголовки
        if stripped.startswith('# '):
            html_lines.append(f'<h1>{_inline_md(stripped[2:])}</h1>')
        elif stripped.startswith('## '):
            html_lines.append(f'<h2>{_inline_md(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            html_lines.append(f'<h3>{_inline_md(stripped[4:])}</h3>')
        elif stripped.startswith('#### '):
            html_lines.append(f'<h4>{_inline_md(stripped[5:])}</h4>')
        # Таблицы
        elif stripped.startswith('|') and '|' in stripped[1:]:
            # Пропускаем разделитель таблицы
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            row = '<tr>' + ''.join(f'<td>{_inline_md(c)}</td>' for c in cells) + '</tr>'
            if not in_list:
                html_lines.append('<table class="table table-sm table-bordered">')
                in_list = True
            html_lines.append(row)
        # Списки
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{_inline_md(stripped[2:])}</li>')
        elif re.match(r'^\d+\.\s', stripped):
            content = re.sub(r'^\d+\.\s', '', stripped)
            if not in_list:
                html_lines.append('<ol>')
                in_list = True
            html_lines.append(f'<li>{_inline_md(content)}</li>')
        # Горизонтальная линия
        elif stripped == '---' or stripped == '***':
            html_lines.append('<hr>')
        # Абзацы
        else:
            html_lines.append(f'<p>{_inline_md(stripped)}</p>')

    if in_list:
        html_lines.append('</ul>' if '</li>' in html_lines[-1] else '</table>')

    return '\n'.join(html_lines)


def _inline_md(text):
    """Конвертация inline MD форматирования"""
    # Код
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Жирный
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Курсив
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    # Ссылки
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def index(data, session):
    """Главная страница документации — список файлов"""
    docs_dir = get_global('starter_path') / 'files' / 'docs'
    if not docs_dir.exists():
        return render_template_string('<div class="container-fluid p-4"><h3>Документация не найдена</h3></div>')

    files = []
    for f in sorted(docs_dir.glob('*.md')):
        # Читаем первую строку как название
        try:
            first_line = f.read_text(encoding='utf-8').split('\n')[0].strip('# ').strip()
        except Exception:
            first_line = f.stem
        files.append({
            'name': f.stem,
            'title': first_line,
            'filename': f.name,
        })

    return render_template_string(DOCS_INDEX_TEMPLATE, files=files, t=t)


DOC_INDEX_HTML = '''{% extends "layout.html" %}
{% block content %}
<div class="container-fluid p-4">
    <h3><i class="bi bi-book me-2"></i> Документация</h3>
    <div class="row mt-3">
        {% for f in files %}
        <div class="col-md-4 mb-3">
            <a href="#" class="text-decoration-none" onclick="loadDoc('{{ f.name }}'); return false;">
                <div class="card h-100 border-primary">
                    <div class="card-body">
                        <h5 class="card-title"><i class="bi bi-file-earmark-text me-2"></i>{{ f.title }}</h5>
                        <p class="card-text text-muted small">{{ f.filename }}</p>
                    </div>
                </div>
            </a>
        </div>
        {% endfor %}
    </div>
    <div id="docContent" class="mt-4" style="display:none;">
        <div class="card">
            <div class="card-header d-flex justify-content-between">
                <span id="docTitle"></span>
                <button class="btn btn-sm btn-outline-secondary" onclick="$('#docContent').hide()">Назад</button>
            </div>
            <div class="card-body" id="docBody" style="max-height:70vh;overflow-y:auto;"></div>
        </div>
    </div>
</div>
<script>
function loadDoc(name) {
    $.post('/', {section: 'docs', action: 'view', doc: name}, function(res) {
        if (res.status === 'success') {
            $('#docTitle').text(res.title);
            $('#docBody').html(res.html);
            $('#docContent').show();
            $('html,body').animate({scrollTop: $('#docContent').offset().top - 80}, 300);
        }
    });
}
</script>
{% endblock %}'''


def view(data, session):
    """Просмотр конкретного MD файла"""
    doc_name = data.get('doc', 'index')
    docs_dir = get_global('starter_path') / 'files' / 'docs'
    doc_path = docs_dir / f'{doc_name}.md'

    if not doc_path.exists():
        return jsonify({'status': 'error', 'message': f'Document not found: {doc_name}'})

    try:
        content = doc_path.read_text(encoding='utf-8')
        title = content.split('\n')[0].strip('# ').strip()
        html = _md_to_html(content)
        return jsonify({'status': 'success', 'title': title, 'html': html})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


DOCS_INDEX_TEMPLATE = DOC_INDEX_HTML
