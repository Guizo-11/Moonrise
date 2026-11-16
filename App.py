# Biblioteca de mangás/HQs - versão simples (Flask + SQLite)
#
# Como usar:
#   1) pip install flask
#   2) python app.py
#   3) abrir no navegador: http://127.0.0.1:5000
#
# Admin: entre em /login com a senha definida em SENHA_ADMIN (abaixo).
# Estrutura: OBRA -> CAPÍTULOS -> PÁGINAS (imagens)

import os
import sqlite3
from flask import Flask, request, redirect, session, render_template_string

app = Flask(__name__)
app.secret_key = "qualquer-coisa-aqui"
SENHA_ADMIN = "Senha123"  # troque essa senha

# Caminhos das pastas e do banco
BASE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(BASE, "biblioteca.db")
PASTA_IMAGENS = os.path.join(BASE, "static", "imagens")
os.makedirs(PASTA_IMAGENS, exist_ok=True)


# ---------- Funções do banco de dados ----------
def ler(sql, params=()):
    """Faz um SELECT e devolve uma lista de linhas."""
    con = sqlite3.connect(BANCO)
    con.row_factory = sqlite3.Row
    linhas = con.execute(sql, params).fetchall()
    con.close()
    return linhas


def gravar(sql, params=()):
    """Faz INSERT/CREATE e devolve o id criado."""
    con = sqlite3.connect(BANCO)
    cursor = con.execute(sql, params)
    con.commit()
    novo_id = cursor.lastrowid
    con.close()
    return novo_id


def criar_tabelas():
    gravar("""CREATE TABLE IF NOT EXISTS obra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT, autor TEXT, descricao TEXT)""")
    gravar("""CREATE TABLE IF NOT EXISTS capitulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER, numero INTEGER, titulo TEXT)""")
    gravar("""CREATE TABLE IF NOT EXISTS pagina (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capitulo_id INTEGER, numero INTEGER, arquivo TEXT)""")


# ---------- Topo comum das páginas (HTML) ----------
TOPO = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Biblioteca</title>
<style>
 body{font-family:sans-serif;max-width:800px;margin:auto;padding:10px;background:#f4f4f4}
 img{max-width:100%;display:block;margin:auto}
 input,textarea{width:100%;margin:4px 0 10px;padding:6px;box-sizing:border-box}
 .caixa{background:white;padding:10px;margin:8px 0;border-radius:6px}
</style></head><body>
<h2><a href="/">📖 Biblioteca</a></h2>
<p>{% if session.get('admin') %}<a href="/admin">Painel</a> | <a href="/sair">Sair</a>
{% else %}<a href="/login">Admin</a>{% endif %}</p>
"""


# ---------- ÁREA DO LEITOR ----------
@app.route("/")
def inicio():
    busca = request.args.get("q", "")
    obras = ler("SELECT * FROM obra WHERE titulo LIKE ? OR autor LIKE ? ORDER BY titulo",
                (f"%{busca}%", f"%{busca}%"))
    return render_template_string(TOPO + """
    <form><input name="q" value="{{ busca }}" placeholder="Pesquisar obra ou autor">
    <button>Buscar</button></form>
    {% for o in obras %}
      <div class="caixa">
        <h3><a href="/obra/{{ o.id }}">{{ o.titulo }}</a></h3>
        <small>{{ o.autor }}</small>
        <p>{{ o.descricao }}</p>
      </div>
    {% else %}<p>Nenhuma obra encontrada.</p>{% endfor %}
    """, obras=obras, busca=busca)


@app.route("/obra/<int:obra_id>")
def ver_obra(obra_id):
    obra = ler("SELECT * FROM obra WHERE id = ?", (obra_id,))
    if not obra:
        return "Obra não encontrada", 404
    capitulos = ler("SELECT * FROM capitulo WHERE obra_id = ? ORDER BY numero", (obra_id,))
    return render_template_string(TOPO + """
    <h2>{{ obra.titulo }}</h2>
    <small>{{ obra.autor }}</small>
    <p>{{ obra.descricao }}</p>
    <h3>Capítulos</h3>
    {% for c in capitulos %}
      <div class="caixa"><a href="/ler/{{ c.id }}">Capítulo {{ c.numero }} - {{ c.titulo }}</a></div>
    {% else %}<p>Nenhum capítulo ainda.</p>{% endfor %}
    """, obra=obra[0], capitulos=capitulos)


@app.route("/ler/<int:cap_id>")
def ler_capitulo(cap_id):
    cap = ler("SELECT * FROM capitulo WHERE id = ?", (cap_id,))
    if not cap:
        return "Capítulo não encontrado", 404
    cap = cap[0]
    paginas = ler("SELECT * FROM pagina WHERE capitulo_id = ? ORDER BY numero", (cap_id,))
    anterior = ler("SELECT id FROM capitulo WHERE obra_id = ? AND numero < ? "
                   "ORDER BY numero DESC LIMIT 1", (cap["obra_id"], cap["numero"]))
    proximo = ler("SELECT id FROM capitulo WHERE obra_id = ? AND numero > ? "
                  "ORDER BY numero LIMIT 1", (cap["obra_id"], cap["numero"]))
    return render_template_string(TOPO + """
    <p><a href="/obra/{{ cap.obra_id }}">← Voltar para a obra</a></p>
    <h3>Capítulo {{ cap.numero }} - {{ cap.titulo }}</h3>
    {% for p in paginas %}
      <img src="/static/imagens/{{ p.arquivo }}">
    {% endfor %}
    <p>
      {% if anterior %}<a href="/ler/{{ anterior[0].id }}">← Capítulo anterior</a>{% endif %}
      {% if proximo %} | <a href="/ler/{{ proximo[0].id }}">Próximo capítulo →</a>{% endif %}
    </p>
    """, cap=cap, paginas=paginas, anterior=anterior, proximo=proximo)


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        if request.form["senha"] == SENHA_ADMIN:
            session["admin"] = True
            return redirect("/admin")
        erro = "Senha incorreta."
    return render_template_string(TOPO + """
    <h3>Login do admin</h3><p style="color:red">{{ erro }}</p>
    <form method="post">
      <input type="password" name="senha" placeholder="Senha">
      <button>Entrar</button>
    </form>""", erro=erro)


@app.route("/sair")
def sair():
    session.clear()
    return redirect("/")


# ---------- ÁREA DO ADMIN ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect("/login")
    if request.method == "POST":  # cadastrar nova obra
        gravar("INSERT INTO obra (titulo, autor, descricao) VALUES (?, ?, ?)",
               (request.form["titulo"], request.form["autor"], request.form["descricao"]))
        return redirect("/admin")
    obras = ler("SELECT * FROM obra ORDER BY titulo")
    return render_template_string(TOPO + """
    <h3>Nova obra</h3>
    <form method="post">
      <input name="titulo" placeholder="Título" required>
      <input name="autor" placeholder="Autor" required>
      <textarea name="descricao" placeholder="Descrição"></textarea>
      <button>Cadastrar obra</button>
    </form>
    <h3>Obras cadastradas</h3>
    {% for o in obras %}
      <div class="caixa">{{ o.titulo }} - <a href="/admin/obra/{{ o.id }}">Adicionar capítulos</a></div>
    {% endfor %}
    """, obras=obras)


@app.route("/admin/obra/<int:obra_id>", methods=["GET", "POST"])
def admin_obra(obra_id):
    if not session.get("admin"):
        return redirect("/login")
    obra = ler("SELECT * FROM obra WHERE id = ?", (obra_id,))
    if not obra:
        return "Obra não encontrada", 404

    if request.method == "POST":  # cadastrar capítulo + imagens
        cap_id = gravar("INSERT INTO capitulo (obra_id, numero, titulo) VALUES (?, ?, ?)",
                        (obra_id, request.form["numero"], request.form["titulo"]))
        # as páginas ficam na ordem do nome do arquivo (01.jpg, 02.jpg, ...)
        arquivos = sorted(request.files.getlist("imagens"), key=lambda f: f.filename)
        numero_pagina = 0
        for arq in arquivos:
            extensao = arq.filename.rsplit(".", 1)[-1].lower()
            if extensao not in ("jpg", "jpeg", "png", "webp", "gif"):
                continue  # ignora o que não for imagem
            numero_pagina += 1
            nome = f"{cap_id}_{numero_pagina}.{extensao}"
            arq.save(os.path.join(PASTA_IMAGENS, nome))
            gravar("INSERT INTO pagina (capitulo_id, numero, arquivo) VALUES (?, ?, ?)",
                   (cap_id, numero_pagina, nome))
        return redirect(f"/admin/obra/{obra_id}")

    capitulos = ler("SELECT * FROM capitulo WHERE obra_id = ? ORDER BY numero", (obra_id,))
    return render_template_string(TOPO + """
    <h3>{{ obra.titulo }}</h3>
    <form method="post" enctype="multipart/form-data">
      <input name="numero" type="number" placeholder="Número do capítulo" required>
      <input name="titulo" placeholder="Título do capítulo">
      <p>Páginas (nomeie como 01.jpg, 02.jpg, 03.jpg...):</p>
      <input type="file" name="imagens" multiple required>
      <button>Enviar capítulo</button>
    </form>
    <h3>Capítulos</h3>
    {% for c in capitulos %}
      <div class="caixa"><a href="/ler/{{ c.id }}">Capítulo {{ c.numero }} - {{ c.titulo }}</a></div>
    {% endfor %}
    <p><a href="/admin">← Voltar</a></p>
    """, obra=obra[0], capitulos=capitulos)


# ---------- Iniciar o programa ----------
if __name__ == "__main__":
    criar_tabelas()
    app.run(debug=True)
