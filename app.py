
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import sqlite3, os, zipfile, shutil, re, secrets

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.db")
UPLOAD_IMG = os.path.join(APP_DIR, "uploads", "imagens")
UPLOAD_IMG = os.path.join(APP_DIR, "uploads", "imagens")
UPLOAD_CHAMADOS = os.path.join(APP_DIR, "uploads", "chamados")
UPLOAD_WORD = os.path.join(APP_DIR, "uploads", "word")
GENERATED_WORD_DIR = os.path.join(APP_DIR, "static", "generated_word")
BACKUP_DIR = os.path.join(APP_DIR, "backups")

app = Flask(__name__)
app.secret_key = "portal-erasmo-supremo-troque-em-producao"
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024

IMG_EXT = {"png","jpg","jpeg","webp","gif"}
IMG_EXT = {"png","jpg","jpeg","webp","gif"}
CHAMADO_EXT = {"pdf","png","jpg","jpeg","webp","gif","txt"}
WORD_EXT = {"docx"}

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def today(): return datetime.now().strftime("%Y-%m-%d")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def allowed(name, exts):
    return "." in name and name.rsplit(".", 1)[1].lower() in exts

def col_exists(conn, table, col):
    return any(row["name"] == col for row in conn.execute(f"PRAGMA table_info({table})").fetchall())

def add_col(conn, table, col, ddl):
    if not col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

def init_db():
    os.makedirs(UPLOAD_IMG, exist_ok=True)
    os.makedirs(UPLOAD_CHAMADOS, exist_ok=True)
    os.makedirs(UPLOAD_WORD, exist_ok=True)
    os.makedirs(GENERATED_WORD_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS setores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            descricao TEXT DEFAULT '',
            aviso TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1,
            criado_em TEXT
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil TEXT DEFAULT 'funcionario',
            setor_id INTEGER,
            tema TEXT DEFAULT 'ocean',
            ativo INTEGER DEFAULT 1,
            criado_em TEXT,
            FOREIGN KEY(setor_id) REFERENCES setores(id)
        );
        CREATE TABLE IF NOT EXISTS pastas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setor_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            criado_em TEXT,
            FOREIGN KEY(setor_id) REFERENCES setores(id)
        );
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pasta_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            tipo TEXT DEFAULT 'html',
            html TEXT DEFAULT '',
            arquivo_nome TEXT DEFAULT '',
            arquivo_path TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            atualizado_por TEXT DEFAULT '',
            atualizado_em TEXT,
            deletado INTEGER DEFAULT 0,
            criado_em TEXT,
            FOREIGN KEY(pasta_id) REFERENCES pastas(id)
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            acao TEXT NOT NULL,
            criado_em TEXT
        );
        CREATE TABLE IF NOT EXISTS leituras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            conteudo_id INTEGER NOT NULL,
            lido_em TEXT,
            UNIQUE(usuario_id, conteudo_id)
        );
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            conteudo_id INTEGER,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            status TEXT DEFAULT 'aberto',
            criado_em TEXT,
            resolvido_em TEXT
        );
        CREATE TABLE IF NOT EXISTS versoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conteudo_id INTEGER,
            titulo TEXT,
            descricao TEXT,
            html TEXT,
            tags TEXT,
            salvo_por TEXT,
            salvo_em TEXT
        );

        CREATE TABLE IF NOT EXISTS chamado_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chamado_id INTEGER NOT NULL,
            usuario_id INTEGER,
            mensagem TEXT NOT NULL,
            criado_em TEXT,
            FOREIGN KEY(chamado_id) REFERENCES chamados(id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setor_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            prioridade TEXT DEFAULT 'normal',
            ativo INTEGER DEFAULT 1,
            criado_por TEXT DEFAULT '',
            criado_em TEXT,
            FOREIGN KEY(setor_id) REFERENCES setores(id)
        );
        """)

        add_col(conn, "usuarios", "must_change_password", "INTEGER DEFAULT 0")
        add_col(conn, "usuarios", "ultimo_login", "TEXT DEFAULT ''")
        add_col(conn, "usuarios", "permissoes", "TEXT DEFAULT ''")
        add_col(conn, "conteudos", "obrigatorio", "INTEGER DEFAULT 0")
        add_col(conn, "conteudos", "prioridade", "TEXT DEFAULT 'normal'")
        add_col(conn, "conteudos", "status", "TEXT DEFAULT 'publicado'")
        add_col(conn, "conteudos", "revisar_em", "TEXT DEFAULT ''")
        add_col(conn, "conteudos", "arquivo_word_path", "TEXT DEFAULT ''")
        add_col(conn, "chamados", "setor_id", "INTEGER")
        add_col(conn, "chamados", "arquivo_nome", "TEXT DEFAULT ''")
        add_col(conn, "chamados", "arquivo_path", "TEXT DEFAULT ''")
        add_col(conn, "chamados", "prioridade", "TEXT DEFAULT 'normal'")

        if conn.execute("SELECT COUNT(*) total FROM setores").fetchone()["total"] == 0:
            setores = [
                ("Marcação","marcacao","Guias, convênios e rotinas para a equipe de Marcação.","Consulte as orientações de convênios antes de finalizar uma marcação."),
                ("Faturamento","faturamento","Guias e processos do setor de Faturamento.","Confira sempre se os documentos estão atualizados antes do envio."),
                ("Financeiro","financeiro","Procedimentos e documentos internos do Financeiro.","Use os procedimentos internos como referência para conferências financeiras."),
                ("Apoio","apoio","Documentos e comunicados do setor de Apoio.","Comunicados e documentos gerais ficam disponíveis nesta área."),
                ("Recepção","recepcao","Guias e processos da Recepção.","Consulte os fluxos de atendimento antes de orientar pacientes."),
                ("Conferência","conferencia","Processos e checklists de conferência.","Verifique os checklists antes de finalizar processos.")
            ]
            for s in setores:
                conn.execute("INSERT INTO setores(nome,slug,descricao,aviso,criado_em) VALUES(?,?,?,?,?)", (*s, now()))

            default_folders = {
                "marcacao":["Convênios","Rotinas","Comunicados"],
                "faturamento":["Guias","Notas","Pendências"],
                "financeiro":["Procedimentos","Relatórios","Comunicados"],
                "apoio":["Documentos","Rotinas"],
                "recepcao":["Atendimento","Agendamentos","Comunicados"],
                "conferencia":["Processos","Checklists"]
            }
            for slug, folders in default_folders.items():
                setor = conn.execute("SELECT id FROM setores WHERE slug=?", (slug,)).fetchone()
                for f in folders:
                    conn.execute("INSERT INTO pastas(setor_id,nome,descricao,criado_em) VALUES(?,?,?,?)",
                                 (setor["id"], f, f"Pasta de {f} do setor.", now()))

            pasta = conn.execute("""
                SELECT pastas.id FROM pastas JOIN setores ON setores.id=pastas.setor_id
                WHERE setores.slug='marcacao' AND pastas.nome='Convênios'
            """).fetchone()["id"]
            conn.execute("""
                INSERT INTO conteudos(pasta_id,titulo,descricao,tipo,html,tags,atualizado_por,atualizado_em,criado_em,obrigatorio,prioridade,status,revisar_em)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (pasta, "Atendimentos P e PP", "Orientações iniciais para atendimentos P e PP.", "html",
                  "<h1>Atendimentos P e PP</h1><p>Esta é uma página inicial da intranet.</p><div class='callout'><strong>Importante:</strong><p>Use o admin para editar, anexar PDF, tornar obrigatório e acompanhar leituras.</p></div>",
                  "convênio,marcação,obrigatório", "Sistema", today(), now(), 1, "importante", "publicado", "2026-12-31"))

        def ensure_user(nome, usuario, senha, perfil, setor_slug=None, tema="ocean", must=0):
            if conn.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone():
                return
            setor_id = None
            if setor_slug:
                setor = conn.execute("SELECT id FROM setores WHERE slug=?", (setor_slug,)).fetchone()
                setor_id = setor["id"] if setor else None
            conn.execute("""
                INSERT INTO usuarios(nome,usuario,senha_hash,perfil,setor_id,tema,ativo,criado_em,must_change_password)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (nome, usuario, generate_password_hash(senha), perfil, setor_id, tema, 1, now(), must))

        ensure_user("Val", "val", "Erasmo@Adm2026", "admin", None, "ocean", 0)
        ensure_user("Alef", "alef", "Alef@2026", "admin", None, "ocean", 0)
        ensure_user("Equipe Marcação", "marcacao", "Marca@2026", "funcionario", "marcacao", "forest", 0)
        ensure_user("Equipe Faturamento", "faturamento", "Fatura#2026", "funcionario", "faturamento", "ocean", 0)
        ensure_user("Equipe Financeiro", "financeiro", "Finan@2026", "funcionario", "financeiro", "forest", 0)
        ensure_user("Equipe Apoio", "apoio", "Apoio#2026", "funcionario", "apoio", "forest", 0)
        ensure_user("Equipe Recepção", "recepcao", "Recep@2026", "funcionario", "recepcao", "ocean", 0)
        ensure_user("Equipe Conferência", "conferencia", "Confere#2026", "funcionario", "conferencia", "forest", 0)

        conn.commit()

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    with db() as conn:
        return conn.execute("""
            SELECT usuarios.*, setores.nome setor_nome, setores.slug setor_slug
            FROM usuarios LEFT JOIN setores ON setores.id=usuarios.setor_id
            WHERE usuarios.id=?
        """, (uid,)).fetchone()

def log(acao):
    with db() as conn:
        conn.execute("INSERT INTO logs(usuario_id,acao,criado_em) VALUES(?,?,?)", (session.get("user_id"), acao, now()))
        conn.commit()

def login_required(fn):
    @wraps(fn)
    def wrap(*a, **kw):
        if not session.get("user_id"): return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrap

def admin_required(fn):
    @wraps(fn)
    def wrap(*a, **kw):
        u = current_user()
        if not u or u["perfil"] != "admin": abort(403)
        return fn(*a, **kw)
    return wrap


def slugify(text):
    text = (text or "documento").lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text or "documento"



def converter_word_para_html(docx_path, titulo):
    """
    Converte arquivo Word .docx em HTML interno.
    Mantém títulos, parágrafos, listas, tabelas simples e imagens embutidas quando possível.
    Usa mammoth, que é próprio para converter DOCX para HTML.
    """
    try:
        import mammoth
    except Exception:
        return f"""
        <h1>{titulo}</h1>
        <div class="callout warning">
            <strong>Documento Word anexado:</strong>
            <p>Para converter o Word automaticamente em HTML, instale a dependência mammoth.</p>
            <p>Rode: <code>python -m pip install -r requirements.txt</code></p>
        </div>
        """

    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value

    if not html.strip():
        html = "<p>O documento Word foi anexado, mas não foi possível extrair conteúdo automaticamente.</p>"

    return f"""
    <article class="word-document">
        <h1>{titulo}</h1>
        <div class="doc-note">
            Documento Word convertido automaticamente em página HTML interna.
        </div>
        {html}
    </article>
    """



# ============================================================
# LDAP / ACTIVE DIRECTORY
# ============================================================

def load_ldap_config():
    """
    Carrega configurações do arquivo ldap_config.py.
    Se o arquivo não existir, o login continua funcionando em modo local.
    """
    cfg = {
        "LDAP_ENABLED": False,
        "LDAP_SERVER": "",
        "LDAP_PORT": 389,
        "LDAP_USE_SSL": False,
        "LDAP_DOMAIN": "",
        "LDAP_BASE_DN": "",
        "LDAP_BIND_USER": "",
        "LDAP_BIND_PASSWORD": "",
        "LDAP_USER_SEARCH_FILTER": "(sAMAccountName={username})",
        "LDAP_GROUP_ATTRIBUTE": "memberOf",
        "LDAP_ADMIN_GROUPS": [],
        "LDAP_SETOR_GROUPS": {},
        "LDAP_PERMISSION_GROUPS": {}
    }

    path = os.path.join(APP_DIR, "ldap_config.py")
    if os.path.exists(path):
        data = {}
        with open(path, "r", encoding="utf-8") as f:
            exec(f.read(), data)
        for k in cfg.keys():
            if k in data:
                cfg[k] = data[k]

    return cfg

LDAP_CONFIG = load_ldap_config()

def ldap_disponivel():
    return bool(LDAP_CONFIG.get("LDAP_ENABLED"))

def normalizar_usuario_ldap(usuario):
    """
    Aceita:
    - usuario
    - DOMINIO\\usuario
    - usuario@dominio.local

    Retorna apenas o nome curto para busca no AD.
    """
    usuario = (usuario or "").strip()
    if "\\" in usuario:
        usuario = usuario.split("\\", 1)[1]
    if "@" in usuario:
        usuario = usuario.split("@", 1)[0]
    return usuario.lower()

def autenticar_ldap(usuario, senha):
    """
    Autentica no Active Directory via ldap3.
    Retorno:
    {
      ok: bool,
      username: str,
      nome: str,
      email: str,
      grupos: list[str],
      erro: st
    }
    """
    if not ldap_disponivel():
        return {"ok": False, "erro": "LDAP desativado"}

    if not usuario or not senha:
        return {"ok": False, "erro": "Usuário ou senha vazios"}

    try:
        from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
    except Exception:
        return {"ok": False, "erro": "Dependência ldap3 não instalada"}

    cfg = LDAP_CONFIG
    username = normalizar_usuario_ldap(usuario)

    try:
        server = Server(
            cfg["LDAP_SERVER"],
            port=int(cfg.get("LDAP_PORT", 389)),
            use_ssl=bool(cfg.get("LDAP_USE_SSL", False)),
            get_info=ALL
        )

        # Conta de serviço para localizar o usuário no AD.
        bind_user = cfg.get("LDAP_BIND_USER") or ""
        bind_password = cfg.get("LDAP_BIND_PASSWORD") or ""

        if bind_user and bind_password:
            conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
        else:
            # Sem bind de serviço: tenta bind direto com o usuário.
            domain = cfg.get("LDAP_DOMAIN", "")
            user_login = f"{domain}\\{username}" if domain and "\\" not in usuario and "@" not in usuario else usuario
            conn = Connection(server, user=user_login, password=senha, authentication=NTLM, auto_bind=True)

        search_filter = cfg.get("LDAP_USER_SEARCH_FILTER", "(sAMAccountName={username})").format(username=username)
        conn.search(
            cfg["LDAP_BASE_DN"],
            search_filter,
            search_scope=SUBTREE,
            attributes=["cn", "displayName", "mail", "memberOf", "sAMAccountName", "userPrincipalName"]
        )

        if not conn.entries:
            return {"ok": False, "erro": "Usuário não encontrado no AD"}

        entry = conn.entries[0]
        user_dn = entry.entry_dn

        # Se usou conta de serviço, agora valida a senha do usuário.
        if bind_user and bind_password:
            domain = cfg.get("LDAP_DOMAIN", "")
            user_login = f"{domain}\\{username}" if domain else username
            test_conn = Connection(server, user=user_login, password=senha, authentication=NTLM, auto_bind=True)
            test_conn.unbind()

        grupos = []
        if hasattr(entry, "memberOf"):
            try:
                grupos = [str(g) for g in entry.memberOf.values]
            except Exception:
                grupos = []

        nome = ""
        if hasattr(entry, "displayName") and entry.displayName:
            nome = str(entry.displayName)
        elif hasattr(entry, "cn") and entry.cn:
            nome = str(entry.cn)
        else:
            nome = username

        email = str(entry.mail) if hasattr(entry, "mail") and entry.mail else ""

        conn.unbind()

        return {
            "ok": True,
            "username": username,
            "nome": nome,
            "email": email,
            "grupos": grupos,
            "dn": user_dn,
            "erro": ""
        }

    except Exception as e:
        return {"ok": False, "erro": str(e)}

def pertence_a_grupo(grupos_usuario, grupos_config):
    """
    Compara grupos do usuário com grupos configurados.
    Aceita comparação por:
    - DN completo: CN=Intranet_Admin,OU=Grupos,DC=clinica,DC=local
    - nome parcial: Intranet_Admin
    """
    if not grupos_config:
        return False

    grupos_usuario_lower = [g.lower() for g in grupos_usuario]
    for grupo in grupos_config:
        grupo_lower = str(grupo).lower()
        for gu in grupos_usuario_lower:
            if grupo_lower == gu or grupo_lower in gu:
                return True
    return False

def mapear_ldap_para_usuario(info):
    """
    Define perfil, setor e permissões a partir dos grupos do AD.
    """
    cfg = LDAP_CONFIG
    grupos = info.get("grupos", [])

    perfil = "funcionario"
    setor_slug = None
    permissoes = []

    if pertence_a_grupo(grupos, cfg.get("LDAP_ADMIN_GROUPS", [])):
        perfil = "admin"

    for slug, grupos_setor in cfg.get("LDAP_SETOR_GROUPS", {}).items():
        if pertence_a_grupo(grupos, grupos_setor):
            setor_slug = slug
            break

    for perm, grupos_perm in cfg.get("LDAP_PERMISSION_GROUPS", {}).items():
        if perm in PERMISSOES_DISPONIVEIS and pertence_a_grupo(grupos, grupos_perm):
            permissoes.append(perm)

    return perfil, setor_slug, permissoes

def obter_ou_criar_usuario_ldap(info):
    """
    Cria ou atualiza usuário local espelhado do AD.
    A senha não é usada localmente para esses usuários.
    O banco local continua guardando tema, permissões extras, logs etc.
    """
    username = info["username"]
    nome = info["nome"]

    perfil, setor_slug, permissoes_ldap = mapear_ldap_para_usuario(info)

    with db() as conn:
        setor_id = None
        if setor_slug:
            setor = conn.execute("SELECT id FROM setores WHERE slug=?", (setor_slug,)).fetchone()
            setor_id = setor["id"] if setor else None

        existente = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (username,)).fetchone()

        if existente:
            # Mantém permissões manuais do painel e soma com permissões do AD.
            atuais = set((existente["permissoes"] or "").split(",")) if "permissoes" in existente.keys() else set()
            novas = atuais.union(set(permissoes_ldap))
            conn.execute("""
                UPDATE usuarios
                SET nome=?, perfil=?, setor_id=?, ativo=1, ultimo_login=?, permissoes=?
                WHERE id=?
            """, (nome, perfil, setor_id, now(), ",".join(sorted([p for p in novas if p])), existente["id"]))
            conn.commit()
            return conn.execute("SELECT * FROM usuarios WHERE id=?", (existente["id"],)).fetchone()

        senha_fake = generate_password_hash(secrets.token_urlsafe(32))
        conn.execute("""
            INSERT INTO usuarios(nome,usuario,senha_hash,perfil,setor_id,tema,ativo,criado_em,must_change_password,ultimo_login,permissoes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (nome, username, senha_fake, perfil, setor_id, "ocean", 1, now(), 0, now(), ",".join(permissoes_ldap)))
        conn.commit()

        return conn.execute("SELECT * FROM usuarios WHERE usuario=?", (username,)).fetchone()

def login_local_emergencia(usuario, senha):
    """
    Usuários locais de emergência.
    Mesmo com LDAP ligado, estes usuários continuam entrando pelo banco local:
    - val
    - alef
    """
    usuario = (usuario or "").strip().lower()
    if usuario not in ["val", "alef"]:
        return None

    with db() as conn:
        u = conn.execute("SELECT * FROM usuarios WHERE usuario=? AND ativo=1", (usuario,)).fetchone()

    if u and check_password_hash(u["senha_hash"], senha):
        return u

    return None


PERMISSOES_DISPONIVEIS = {
    "anexar_documentos": "Anexar documentos",
    "editar_documentos": "Editar documentos",
    "excluir_documentos": "Excluir documentos",
    "criar_pastas": "Criar pastas",
    "editar_pastas": "Editar pastas",
    "excluir_pastas": "Excluir pastas",
    "criar_avisos": "Criar avisos",
    "editar_avisos": "Editar avisos",
    "excluir_avisos": "Excluir avisos",
    "ver_lixeira": "Acessar lixeira",
    "restaurar_lixeira": "Restaurar lixeira",
    "gerenciar_usuarios": "Gerenciar usuários",
    "gerar_backup": "Gerar backup",
    "ver_logs": "Ver logs",
    "upload_imagem": "Enviar imagens"
}

def permissoes_usuario(user=None):
    user = user or current_user()
    if not user:
        return set()
    if user["perfil"] == "admin":
        return set(PERMISSOES_DISPONIVEIS.keys())
    raw = user["permissoes"] if "permissoes" in user.keys() else ""
    return {p.strip() for p in (raw or "").split(",") if p.strip()}

def tem_permissao(nome):
    user = current_user()
    if not user:
        return False
    if user["perfil"] == "admin":
        return True
    return nome in permissoes_usuario(user)

def permission_required(nome):
    def decorator(fn):
        @wraps(fn)
        def wrap(*a, **kw):
            if not tem_permissao(nome):
                abort(403)
            return fn(*a, **kw)
        return wrap
    return decorator


@app.context_processor
def inject():
    return {"current_user": current_user(), "tem_permissao": tem_permissao, "permissoes_disponiveis": PERMISSOES_DISPONIVEIS, "permissoes_usuario": permissoes_usuario}

@app.route("/")
def index():
    if session.get("user_id"):
        u = current_user()
        return redirect(url_for("admin") if u["perfil"] == "admin" else url_for("painel"))
    return redirect(url_for("login"))


# ===== LOGIN LDAP/AD - EXPLICAÇÃO PARA CONFIGURAÇÃO =====
# O login LDAP/Active Directory foi preparado para funcionar assim:
#
# 1. Usuários locais de emergência:
#    - val
#    - alef
#    Esses dois usuários continuam autenticando pelo banco local SQLite,
#    mesmo quando o LDAP estiver ativado.
#
# 2. Usuários do domínio:
#    Quando LDAP_ENABLED = True no arquivo ldap_config.py,
#    qualquer outro usuário será autenticado no Active Directory.
#
# 3. Setor do funcionário:
#    O setor é definido pelo grupo do AD configurado em LDAP_SETOR_GROUPS.
#    Exemplo:
#    Se o usuário estiver no grupo Intranet_Recepcao,
#    ele entra automaticamente no setor Recepção.
#
# 4. Admin:
#    Quem estiver no grupo configurado em LDAP_ADMIN_GROUPS
#    entra como administrador.
#
# 5. Permissões:
#    Permissões podem vir de grupos do AD em LDAP_PERMISSION_GROUPS
#    e também podem ser ajustadas manualmente dentro do painel ADM.
#
# Para ativar:
# - Abra ldap_config.py
# - Preencha os dados reais do domínio
# - Troque LDAP_ENABLED = False para LDAP_ENABLED = True
# ==========================================================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario","").strip()
        usuario = normalizar_usuario_ldap(usuario_digitado)
        senha = request.form.get("senha","")

        # 1. Usuários locais de emergência: val e alef.
        u = login_local_emergencia(usuario, senha)

        # 2. Se não for emergência e LDAP estiver ativo, autentica no AD.
        if not u and ldap_disponivel():
            resultado = autenticar_ldap(usuario_digitado, senha)

            if not resultado.get("ok"):
                flash("Usuário ou senha inválidos no domínio. Detalhe: " + resultado.get("erro", ""), "danger")
                return redirect(url_for("login"))

            u = obter_ou_criar_usuario_ldap(resultado)

        # 3. Se LDAP estiver desligado, mantém login local antigo.
        if not u and not ldap_disponivel():
            with db() as conn:
                u = conn.execute("SELECT * FROM usuarios WHERE usuario=? AND ativo=1", (usuario,)).fetchone()

            if not u or not check_password_hash(u["senha_hash"], senha):
                flash("Usuário ou senha inválidos.", "danger")
                return redirect(url_for("login"))

        if not u:
            flash("Usuário sem acesso autorizado à intranet.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = u["id"]

        with db() as conn:
            conn.execute("UPDATE usuarios SET ultimo_login=? WHERE id=?", (now(), u["id"]))
            conn.commit()

        log(f"Login realizado: {usuario}")

        return redirect(url_for("admin") if u["perfil"] == "admin" else url_for("painel"))

    return render_template("login.html")

@app.route("/trocar-senha", methods=["GET","POST"])
@login_required
def trocar_senha():
    if request.method == "POST":
        s1 = request.form.get("senha","")
        s2 = request.form.get("confirmar","")
        if len(s1) < 6 or s1 != s2:
            flash("A senha deve ter pelo menos 6 caracteres e a confirmação deve ser igual.", "danger")
            return redirect(url_for("trocar_senha"))
        with db() as conn:
            conn.execute("UPDATE usuarios SET senha_hash=?, must_change_password=0 WHERE id=?",
                         (generate_password_hash(s1), session["user_id"]))
            conn.commit()
        log("Senha alterada pelo usuário")
        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("index"))
    return render_template("trocar_senha.html")

@app.route("/logout")
@login_required
def logout():
    log("Logout realizado")
    session.clear()
    return redirect(url_for("login"))

@app.route("/tema/<tema>", methods=["POST"])
@login_required
def tema(tema):
    if tema not in ["ocean","forest","clinical","dark"]:
        tema = "ocean"
    with db() as conn:
        conn.execute("UPDATE usuarios SET tema=? WHERE id=?", (tema, session["user_id"]))
        conn.commit()
    flash("Tema alterado.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/painel")
@login_required
def painel():
    u = current_user()
    with db() as conn:
        setores = conn.execute("SELECT * FROM setores WHERE ativo=1 ORDER BY nome").fetchall()
        if u["perfil"] == "admin":
            setor_id = request.args.get("setor_id") or (setores[0]["id"] if setores else None)
        else:
            setor_id = u["setor_id"]
        setor = conn.execute("SELECT * FROM setores WHERE id=?", (setor_id,)).fetchone()
        pastas = conn.execute("SELECT * FROM pastas WHERE setor_id=? ORDER BY nome", (setor["id"],)).fetchall()
        pasta_id = request.args.get("pasta_id")
        pasta_atual = conn.execute("SELECT * FROM pastas WHERE id=? AND setor_id=?", (pasta_id, setor["id"])).fetchone() if pasta_id else None
        if not pasta_atual and pastas: pasta_atual = pastas[0]
        conteudos = conn.execute("""
            SELECT c.*, CASE WHEN l.id IS NULL THEN 0 ELSE 1 END lido
            FROM conteudos c
            JOIN pastas p ON p.id=c.pasta_id
            LEFT JOIN leituras l ON l.conteudo_id=c.id AND l.usuario_id=?
            WHERE p.setor_id=? AND c.deletado=0 AND c.status='publicado'
            ORDER BY CASE c.prioridade WHEN 'urgente' THEN 1 WHEN 'importante' THEN 2 ELSE 3 END, c.titulo
        """, (u["id"], setor["id"])).fetchall()
        favoritos = conn.execute("""
            SELECT c.*, p.nome pasta_nome FROM conteudos c
            JOIN pastas p ON p.id=c.pasta_id
            WHERE p.setor_id=? AND c.deletado=0 AND c.status='publicado'
            ORDER BY c.atualizado_em DESC LIMIT 4
        """, (setor["id"],)).fetchall()
        stats = conn.execute("""
            SELECT
            (SELECT COUNT(*) FROM pastas WHERE setor_id=?) pastas,
            (SELECT COUNT(*) FROM conteudos c JOIN pastas p ON p.id=c.pasta_id WHERE p.setor_id=? AND c.deletado=0) conteudos,
            (SELECT COUNT(*) FROM conteudos c JOIN pastas p ON p.id=c.pasta_id LEFT JOIN leituras l ON l.conteudo_id=c.id AND l.usuario_id=? WHERE p.setor_id=? AND c.obrigatorio=1 AND c.deletado=0 AND l.id IS NULL) pendentes
        """, (setor["id"], setor["id"], u["id"], setor["id"])).fetchone()
        avisos = conn.execute("""
            SELECT * FROM avisos
            WHERE setor_id=? AND ativo=1
            ORDER BY CASE prioridade WHEN 'urgente' THEN 1 WHEN 'importante' THEN 2 ELSE 3 END, id DESC
        """, (setor["id"],)).fetchall()
    return render_template("painel.html", setor=setor, setores=setores, pastas=pastas, pasta_atual=pasta_atual, conteudos=conteudos, favoritos=favoritos, stats=stats, avisos=avisos)


@app.route("/anexo/<int:id>")
@login_required
def abrir_anexo(id):
    u = current_user()
    with db() as conn:
        c = conn.execute("""
            SELECT c.*, p.nome pasta_nome, s.id setor_id, s.nome setor_nome
            FROM conteudos c
            JOIN pastas p ON p.id=c.pasta_id
            JOIN setores s ON s.id=p.setor_id
            WHERE c.id=?
        """, (id,)).fetchone()

    if not c or c["deletado"]:
        abort(404)

    if u["perfil"] != "admin" and u["setor_id"] != c["setor_id"]:
        abort(403)

    return render_template("anexo.html", conteudo=c)

@app.route("/conteudo/<int:id>")
@login_required
def conteudo(id):
    u = current_user()
    with db() as conn:
        c = conn.execute("""
            SELECT c.*, p.nome pasta_nome, s.id setor_id, s.nome setor_nome
            FROM conteudos c JOIN pastas p ON p.id=c.pasta_id JOIN setores s ON s.id=p.setor_id
            WHERE c.id=?
        """, (id,)).fetchone()
        lido = conn.execute("SELECT * FROM leituras WHERE usuario_id=? AND conteudo_id=?", (u["id"], id)).fetchone()
        versoes = conn.execute("SELECT * FROM versoes WHERE conteudo_id=? ORDER BY id DESC LIMIT 8", (id,)).fetchall()
    if not c or c["deletado"]: abort(404)
    if u["perfil"] != "admin" and u["setor_id"] != c["setor_id"]: abort(403)
    return render_template("visualizar.html", conteudo=c, lido=lido, versoes=versoes)

@app.route("/conteudo/<int:id>/confirmar", methods=["POST"])
@login_required
def confirmar_leitura(id):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO leituras(usuario_id,conteudo_id,lido_em) VALUES(?,?,?)", (session["user_id"], id, now()))
        conn.commit()
    log(f"Confirmou leitura do conteúdo ID {id}")
    flash("Leitura confirmada.", "success")
    return redirect(url_for("conteudo", id=id))

@app.route("/conteudo/<int:id>/reportar", methods=["POST"])
@login_required
def reportar(id):
    titulo = request.form.get("titulo","Problema no documento").strip()
    msg = request.form.get("mensagem","").strip()
    if not msg:
        flash("Descreva o problema.", "danger")
        return redirect(url_for("conteudo", id=id))
    with db() as conn:
        conn.execute("INSERT INTO chamados(usuario_id,conteudo_id,titulo,mensagem,status,prioridade,criado_em) VALUES(?,?,?,?,?,?,?)",
                     (session["user_id"], id, titulo, msg, "novo", "normal", now()))
        conn.commit()
    log(f"Reportou problema no conteúdo ID {id}")
    flash("Problema reportado ao admin.", "success")
    return redirect(url_for("conteudo", id=id))

@app.route("/chamados/criar", methods=["POST"])
@login_required
def criar_chamado_setor():
    u = current_user()

    setor_id = request.form.get("setor_id") or u["setor_id"]
    titulo = request.form.get("titulo", "").strip()
    mensagem = request.form.get("mensagem", "").strip()
    prioridade = request.form.get("prioridade", "normal")
    arquivo = request.files.get("arquivo")

    if not titulo or not mensagem:
        flash("Preencha o título e a mensagem do chamado.", "danger")
        return redirect(request.referrer or url_for("painel"))

    arquivo_nome = ""
    arquivo_path = ""

    if arquivo and arquivo.filename:
        if not allowed(arquivo.filename, CHAMADO_EXT):
            flash("Arquivo inválido. Envie PDF, imagem ou TXT.", "danger")
            return redirect(request.referrer or url_for("painel"))

        arquivo_nome = arquivo.filename
        arquivo_path = secure_filename(datetime.now().strftime("%Y%m%d%H%M%S_") + arquivo.filename)
        arquivo.save(os.path.join(UPLOAD_CHAMADOS, arquivo_path))

    with db() as conn:
        conn.execute("""
            INSERT INTO chamados(usuario_id,setor_id,titulo,mensagem,status,prioridade,arquivo_nome,arquivo_path,criado_em)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (u["id"], setor_id, titulo, mensagem, "novo", prioridade, arquivo_nome, arquivo_path, now()))
        conn.commit()

    log(f"Criou chamado do setor: {titulo}")
    flash("Chamado enviado para o admin.", "success")
    return redirect(request.referrer or url_for("painel"))


@app.route("/uploads/word/<path:filename>")
@login_required
def word_original(filename):
    return send_from_directory(UPLOAD_WORD, filename)

@app.route("/uploads/chamados/<path:filename>")
@login_required
def chamado_arquivo(filename):
    return send_from_directory(UPLOAD_CHAMADOS, filename)

@app.route("/uploads/imagens/<path:filename>")
@login_required
def imagem(filename):
    return send_from_directory(UPLOAD_IMG, filename)


@app.route("/admin/avisos/criar", methods=["POST"])
@login_required
@permission_required("criar_avisos")
def criar_aviso_setor():
    setor_id = request.form.get("setor_id")
    titulo = request.form.get("titulo", "").strip()
    mensagem = request.form.get("mensagem", "").strip()
    prioridade = request.form.get("prioridade", "normal")

    if not setor_id or not titulo or not mensagem:
        flash("Preencha setor, título e mensagem do aviso.", "danger")
        return redirect(request.referrer or url_for("painel"))

    with db() as conn:
        conn.execute("""
            INSERT INTO avisos(setor_id,titulo,mensagem,prioridade,ativo,criado_por,criado_em)
            VALUES(?,?,?,?,?,?,?)
        """, (setor_id, titulo, mensagem, prioridade, 1, current_user()["nome"], now()))
        conn.commit()

    log(f"Aviso criado para setor ID {setor_id}: {titulo}")
    flash("Aviso publicado para o setor.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/admin/avisos/<int:id>/editar", methods=["POST"])
@login_required
@permission_required("editar_avisos")
def editar_aviso_setor(id):
    titulo = request.form.get("titulo", "").strip()
    mensagem = request.form.get("mensagem", "").strip()
    prioridade = request.form.get("prioridade", "normal")

    if not titulo or not mensagem:
        flash("Preencha título e mensagem do aviso.", "danger")
        return redirect(request.referrer or url_for("painel"))

    with db() as conn:
        conn.execute("""
            UPDATE avisos
            SET titulo=?, mensagem=?, prioridade=?
            WHERE id=?
        """, (titulo, mensagem, prioridade, id))
        conn.commit()

    flash("Aviso atualizado.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/admin/avisos/<int:id>/excluir", methods=["POST"])
@login_required
@permission_required("excluir_avisos")
def excluir_aviso_setor(id):
    with db() as conn:
        conn.execute("DELETE FROM avisos WHERE id=?", (id,))
        conn.commit()

    flash("Aviso excluído.", "success")
    return redirect(request.referrer or url_for("painel"))


@app.route("/admin")
@login_required
@admin_required
def admin():
    with db() as conn:
        usuarios = conn.execute("SELECT u.*, s.nome setor_nome FROM usuarios u LEFT JOIN setores s ON s.id=u.setor_id ORDER BY u.nome").fetchall()
        setores = conn.execute("SELECT * FROM setores ORDER BY nome").fetchall()
        dash = conn.execute("""
            SELECT
            (SELECT COUNT(*) FROM usuarios) usuarios,
            (SELECT COUNT(*) FROM setores) setores,
            (SELECT COUNT(*) FROM pastas) pastas,
            (SELECT COUNT(*) FROM conteudos WHERE deletado=0) conteudos,
            (SELECT COUNT(*) FROM conteudos WHERE obrigatorio=1 AND deletado=0) obrigatorios
        """).fetchone()
        logs = conn.execute("SELECT logs.*, usuarios.nome usuario_nome FROM logs LEFT JOIN usuarios ON usuarios.id=logs.usuario_id ORDER BY logs.id DESC LIMIT 20").fetchall()
    return render_template("admin.html", usuarios=usuarios, setores=setores, dash=dash, logs=logs)

@app.route("/admin/usuarios/criar", methods=["POST"])
@login_required
@admin_required
def criar_usuario():
    nome = request.form.get("nome","").strip()
    usuario = request.form.get("usuario","").strip().lower()
    senha = request.form.get("senha","")
    perfil = request.form.get("perfil","funcionario")
    setor_id = request.form.get("setor_id") or None
    tema = request.form.get("tema","ocean")
    must = 0
    if not nome or not usuario or not senha:
        flash("Preencha nome, usuário e senha.", "danger"); return redirect(url_for("admin"))
    try:
        with db() as conn:
            conn.execute("INSERT INTO usuarios(nome,usuario,senha_hash,perfil,setor_id,tema,ativo,criado_em,must_change_password) VALUES(?,?,?,?,?,?,?,?,?)",
                         (nome, usuario, generate_password_hash(senha), perfil, setor_id, tema, 1, now(), must))
            conn.commit()
        flash("Usuário criado.", "success")
    except sqlite3.IntegrityError:
        flash("Usuário já existe.", "danger")
    return redirect(url_for("admin"))


@app.route("/admin/usuarios/<int:id>/funcoes", methods=["POST"])
@login_required
@admin_required
def atualizar_funcoes_usuario(id):
    selecionadas = request.form.getlist("permissoes")
    permissoes = ",".join([p for p in selecionadas if p in PERMISSOES_DISPONIVEIS])

    with db() as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE id=?", (id,)).fetchone()
        if not usuario:
            flash("Usuário não encontrado.", "danger")
            return redirect(url_for("admin"))

        if usuario["perfil"] == "admin" or usuario["usuario"] == "val":
            flash("Administrador já possui todas as funções.", "danger")
            return redirect(url_for("admin"))

        conn.execute("UPDATE usuarios SET permissoes=? WHERE id=?", (permissoes, id))
        conn.commit()

    log(f"Funções atualizadas para usuário ID {id}")
    flash("Funções do usuário atualizadas.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/usuarios/<int:id>/senha", methods=["POST"])
@login_required
@admin_required
def trocar_senha_admin(id):
    senha = request.form.get("senha","")
    must = 0
    if not senha:
        flash("Informe a senha.", "danger"); return redirect(url_for("admin"))
    with db() as conn:
        conn.execute("UPDATE usuarios SET senha_hash=?, must_change_password=? WHERE id=?", (generate_password_hash(senha), must, id))
        conn.commit()
    flash("Senha atualizada.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/usuarios/<int:id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_usuario(id):
    with db() as conn:
        u = conn.execute("SELECT * FROM usuarios WHERE id=?", (id,)).fetchone()
        if u and u["usuario"] != "val":
            conn.execute("UPDATE usuarios SET ativo=? WHERE id=?", (0 if u["ativo"] else 1, id))
            conn.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/setores/criar", methods=["POST"])
@login_required
@admin_required
def criar_setor():
    nome, slug = request.form.get("nome","").strip(), request.form.get("slug","").strip().lower()
    desc, aviso = request.form.get("descricao",""), request.form.get("aviso","")
    try:
        with db() as conn:
            conn.execute("INSERT INTO setores(nome,slug,descricao,aviso,criado_em) VALUES(?,?,?,?,?)", (nome, slug, desc, aviso, now()))
            conn.commit()
        flash("Setor criado.", "success")
    except Exception:
        flash("Erro ao criar setor. Confira nome e slug.", "danger")
    return redirect(url_for("admin"))

@app.route("/admin/pastas/criar", methods=["POST"])
@login_required
@permission_required("criar_pastas")
def criar_pasta():
    setor_id, nome, desc = request.form.get("setor_id"), request.form.get("nome","").strip(), request.form.get("descricao","")
    with db() as conn:
        conn.execute("INSERT INTO pastas(setor_id,nome,descricao,criado_em) VALUES(?,?,?,?)", (setor_id, nome, desc, now()))
        conn.commit()
    flash("Pasta criada.", "success")
    return redirect(request.referrer or url_for("admin"))

@app.route("/admin/pastas/<int:id>/editar", methods=["POST"])
@login_required
@permission_required("editar_pastas")
def editar_pasta(id):
    nome = request.form.get("nome", "").strip()
    desc = request.form.get("descricao", "").strip()

    if not nome:
        flash("Informe o nome da pasta.", "danger")
        return redirect(request.referrer or url_for("painel"))

    with db() as conn:
        conn.execute("UPDATE pastas SET nome=?, descricao=? WHERE id=?", (nome, desc, id))
        conn.commit()

    flash("Pasta atualizada.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/admin/pastas/<int:id>/excluir", methods=["POST"])
@login_required
@permission_required("excluir_pastas")
def excluir_pasta(id):
    with db() as conn:
        pasta = conn.execute("SELECT * FROM pastas WHERE id=?", (id,)).fetchone()

        if not pasta:
            flash("Pasta não encontrada.", "danger")
            return redirect(request.referrer or url_for("painel"))

        # Envia os conteúdos da pasta para a lixeira antes de remover a pasta.
        conn.execute("UPDATE conteudos SET deletado=1 WHERE pasta_id=?", (id,))
        conn.execute("DELETE FROM pastas WHERE id=?", (id,))
        conn.commit()

    flash("Pasta excluída. Conteúdos enviados para a lixeira.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/admin/conteudos/criar", methods=["POST"])
@login_required
@permission_required("anexar_documentos")
def criar_conteudo():
    pasta_id = request.form.get("pasta_id")
    titulo = request.form.get("titulo","").strip()
    desc = request.form.get("descricao","")
    tags = request.form.get("tags","")
    html = request.form.get("html","")
    obrigatorio = 1 if request.form.get("obrigatorio") else 0
    prioridade = request.form.get("prioridade","normal")
    status = request.form.get("status","publicado")
    revisar = request.form.get("revisar_em","")
    word = request.files.get("word")
    tipo, arq_nome, arq_path = "html", "", ""

    if word and word.filename:
        if not allowed(word.filename, WORD_EXT):
            flash("Envie apenas arquivos Word no formato .docx.", "danger"); return redirect(request.referrer or url_for("painel"))

        fname_word = secure_filename(datetime.now().strftime("%Y%m%d%H%M%S_") + word.filename)
        word_path = os.path.join(UPLOAD_WORD, fname_word)
        word.save(word_path)

        html = converter_word_para_html(word_path, titulo)
        tipo = "html_word"
        arq_nome = word.filename
        arq_path = fname_word
    with db() as conn:
        conn.execute("""
            INSERT INTO conteudos(pasta_id,titulo,descricao,tipo,html,arquivo_nome,arquivo_path,tags,atualizado_por,atualizado_em,criado_em,obrigatorio,prioridade,status,revisar_em)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pasta_id,titulo,desc,tipo,html,arq_nome,arq_path,tags,current_user()["nome"],today(),now(),obrigatorio,prioridade,status,revisar))
        conn.commit()
    flash("Conteúdo criado.", "success")
    return redirect(request.referrer or url_for("painel"))

@app.route("/admin/conteudos/<int:id>/editar", methods=["POST"])
@login_required
@permission_required("editar_documentos")
def editar_conteudo(id):
    titulo, desc, tags, html = request.form.get("titulo",""), request.form.get("descricao",""), request.form.get("tags",""), request.form.get("html","")
    obrigatorio = 1 if request.form.get("obrigatorio") else 0
    prioridade, status, revisar = request.form.get("prioridade","normal"), request.form.get("status","publicado"), request.form.get("revisar_em","")
    with db() as conn:
        old = conn.execute("SELECT * FROM conteudos WHERE id=?", (id,)).fetchone()
        conn.execute("INSERT INTO versoes(conteudo_id,titulo,descricao,html,tags,salvo_por,salvo_em) VALUES(?,?,?,?,?,?,?)",
                     (id, old["titulo"], old["descricao"], old["html"], old["tags"], current_user()["nome"], now()))
        conn.execute("""
            UPDATE conteudos SET titulo=?,descricao=?,tags=?,html=?,obrigatorio=?,prioridade=?,status=?,revisar_em=?,atualizado_por=?,atualizado_em=? WHERE id=?
        """, (titulo,desc,tags,html,obrigatorio,prioridade,status,revisar,current_user()["nome"],today(),id))
        conn.commit()
    flash("Conteúdo atualizado e versão anterior salva.", "success")
    return redirect(url_for("conteudo", id=id))


@app.route("/admin/anexos/<int:id>/excluir", methods=["POST"])
@login_required
@permission_required("excluir_documentos")
def excluir_anexo_definitivo(id):
    with db() as conn:
        conteudo = conn.execute("SELECT * FROM conteudos WHERE id=?", (id,)).fetchone()

        if not conteudo:
            flash("Anexo não encontrado.", "danger")
            return redirect(request.referrer or url_for("painel"))

        arquivo_path = conteudo["arquivo_path"]
        tipo = conteudo["tipo"]

        # Remove arquivo físico quando existir.
        # Word anexado
        if arquivo_path and tipo == "html_word":
            word_path = os.path.join(UPLOAD_WORD, arquivo_path)
            if os.path.exists(word_path):
                try:
                    os.remove(word_path)
                except OSError:
                    pass

        # Remove registros relacionados
        conn.execute("DELETE FROM leituras WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM versoes WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM chamados WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM conteudos WHERE id=?", (id,))
        conn.commit()

    log(f"Anexo excluído definitivamente ID {id}")
    flash("Anexo excluído definitivamente.", "success")
    return redirect(url_for("painel"))

@app.route("/admin/conteudos/<int:id>/excluir", methods=["POST"])
@login_required
@permission_required("excluir_documentos")
def excluir_conteudo(id):
    with db() as conn:
        conn.execute("UPDATE conteudos SET deletado=1 WHERE id=?", (id,))
        conn.commit()
    flash("Conteúdo enviado para a lixeira.", "success")
    return redirect(url_for("painel"))

@app.route("/admin/lixeira")
@login_required
@permission_required("ver_lixeira")
def lixeira():
    with db() as conn:
        itens = conn.execute("""
            SELECT c.*, p.nome pasta_nome, s.nome setor_nome FROM conteudos c
            JOIN pastas p ON p.id=c.pasta_id JOIN setores s ON s.id=p.setor_id
            WHERE c.deletado=1 ORDER BY c.id DESC
        """).fetchall()
    return render_template("lixeira.html", conteudos=itens)

@app.route("/admin/conteudos/<int:id>/restaurar", methods=["POST"])
@login_required
@permission_required("restaurar_lixeira")
def restaurar(id):
    with db() as conn:
        conn.execute("UPDATE conteudos SET deletado=0 WHERE id=?", (id,))
        conn.commit()
    flash("Conteúdo restaurado.", "success")
    return redirect(url_for("lixeira"))

@app.route("/admin/conteudos/<int:id>/excluir-permanente", methods=["POST"])
@login_required
@permission_required("excluir_documentos")
def excluir_permanente(id):
    with db() as conn:
        conteudo = conn.execute("SELECT * FROM conteudos WHERE id=?", (id,)).fetchone()

        if not conteudo:
            flash("Conteúdo não encontrado.", "danger")
            return redirect(url_for("lixeira"))

        conn.execute("DELETE FROM leituras WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM chamados WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM versoes WHERE conteudo_id=?", (id,))
        conn.execute("DELETE FROM conteudos WHERE id=?", (id,))
        conn.commit()

    flash("Conteúdo excluído definitivamente.", "success")
    return redirect(url_for("lixeira"))

@app.route("/admin/chamados")
@login_required
@admin_required
def chamados():
    with db() as conn:
        itens = conn.execute("""
            SELECT ch.*, u.nome usuario_nome, c.titulo conteudo_titulo, s.nome setor_nome
            FROM chamados ch
            LEFT JOIN usuarios u ON u.id=ch.usuario_id
            LEFT JOIN conteudos c ON c.id=ch.conteudo_id
            LEFT JOIN setores s ON s.id=ch.setor_id
            ORDER BY CASE ch.status WHEN 'novo' THEN 1 WHEN 'pendente' THEN 2 ELSE 3 END, ch.id DESC
        """).fetchall()
    return render_template("chamados.html", chamados=itens)

@app.route("/admin/chamados/<int:id>/resolver", methods=["POST"])
@login_required
@admin_required
def resolver_chamado(id):
    with db() as conn:
        conn.execute("UPDATE chamados SET status='solucionado', resolvido_em=? WHERE id=?", (now(), id))
        conn.commit()
    flash("Chamado resolvido.", "success")
    return redirect(url_for("chamados"))

@app.route("/admin/chamados/<int:id>")
@login_required
@admin_required
def chamado_detalhe(id):
    with db() as conn:
        chamado = conn.execute("""
            SELECT ch.*, u.nome usuario_nome, c.titulo conteudo_titulo, s.nome setor_nome
            FROM chamados ch
            LEFT JOIN usuarios u ON u.id=ch.usuario_id
            LEFT JOIN conteudos c ON c.id=ch.conteudo_id
            LEFT JOIN setores s ON s.id=ch.setor_id
            WHERE ch.id=?
        """, (id,)).fetchone()

        mensagens = conn.execute("""
            SELECT cm.*, u.nome usuario_nome, u.perfil usuario_perfil
            FROM chamado_mensagens cm
            LEFT JOIN usuarios u ON u.id=cm.usuario_id
            WHERE cm.chamado_id=?
            ORDER BY cm.id
        """, (id,)).fetchall()

    if not chamado:
        abort(404)

    return render_template("chamado_detalhe.html", chamado=chamado, mensagens=mensagens)

@app.route("/admin/chamados/<int:id>/mensagem", methods=["POST"])
@login_required
@admin_required
def chamado_mensagem_admin(id):
    mensagem = request.form.get("mensagem", "").strip()
    novo_status = request.form.get("status", "pendente")

    if not mensagem:
        flash("Digite uma resposta.", "danger")
        return redirect(url_for("chamado_detalhe", id=id))

    with db() as conn:
        conn.execute("INSERT INTO chamado_mensagens(chamado_id,usuario_id,mensagem,criado_em) VALUES(?,?,?,?)",
                     (id, session["user_id"], mensagem, now()))
        conn.execute("UPDATE chamados SET status=? WHERE id=?", (novo_status, id))
        conn.commit()

    flash("Resposta enviada no chamado.", "success")
    return redirect(url_for("chamado_detalhe", id=id))

@app.route("/admin/chamados/<int:id>/status", methods=["POST"])
@login_required
@admin_required
def chamado_status(id):
    status = request.form.get("status", "pendente")
    resolvido_em = now() if status == "solucionado" else None

    with db() as conn:
        if resolvido_em:
            conn.execute("UPDATE chamados SET status=?, resolvido_em=? WHERE id=?", (status, resolvido_em, id))
        else:
            conn.execute("UPDATE chamados SET status=? WHERE id=?", (status, id))
        conn.commit()

    flash("Status do chamado atualizado.", "success")
    return redirect(url_for("chamado_detalhe", id=id))

@app.route("/meus-chamados")
@login_required
def meus_chamados():
    with db() as conn:
        itens = conn.execute("""
            SELECT ch.*, s.nome setor_nome, c.titulo conteudo_titulo
            FROM chamados ch
            LEFT JOIN setores s ON s.id=ch.setor_id
            LEFT JOIN conteudos c ON c.id=ch.conteudo_id
            WHERE ch.usuario_id=?
            ORDER BY ch.id DESC
        """, (session["user_id"],)).fetchall()
    return render_template("meus_chamados.html", chamados=itens)

@app.route("/meus-chamados/<int:id>")
@login_required
def meu_chamado_detalhe(id):
    with db() as conn:
        chamado = conn.execute("""
            SELECT ch.*, s.nome setor_nome, c.titulo conteudo_titulo
            FROM chamados ch
            LEFT JOIN setores s ON s.id=ch.setor_id
            LEFT JOIN conteudos c ON c.id=ch.conteudo_id
            WHERE ch.id=? AND ch.usuario_id=?
        """, (id, session["user_id"])).fetchone()

        mensagens = conn.execute("""
            SELECT cm.*, u.nome usuario_nome, u.perfil usuario_perfil
            FROM chamado_mensagens cm
            LEFT JOIN usuarios u ON u.id=cm.usuario_id
            WHERE cm.chamado_id=?
            ORDER BY cm.id
        """, (id,)).fetchall()

    if not chamado:
        abort(404)

    return render_template("meu_chamado_detalhe.html", chamado=chamado, mensagens=mensagens)

@app.route("/meus-chamados/<int:id>/mensagem", methods=["POST"])
@login_required
def meu_chamado_mensagem(id):
    mensagem = request.form.get("mensagem", "").strip()

    if not mensagem:
        flash("Digite uma mensagem.", "danger")
        return redirect(url_for("meu_chamado_detalhe", id=id))

    with db() as conn:
        chamado = conn.execute("SELECT * FROM chamados WHERE id=? AND usuario_id=?", (id, session["user_id"])).fetchone()

        if not chamado:
            abort(403)

        conn.execute("INSERT INTO chamado_mensagens(chamado_id,usuario_id,mensagem,criado_em) VALUES(?,?,?,?)",
                     (id, session["user_id"], mensagem, now()))
        if chamado["status"] == "solucionado":
            conn.execute("UPDATE chamados SET status='pendente' WHERE id=?", (id,))
        conn.commit()

    flash("Mensagem enviada.", "success")
    return redirect(url_for("meu_chamado_detalhe", id=id))



@app.route("/admin/conteudos/<int:id>/editor", methods=["GET", "POST"])
@login_required
@permission_required("editar_documentos")
def editor_visual_conteudo(id):
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        html = request.form.get("html", "")

        if not titulo:
            flash("Informe o título do documento.", "danger")
            return redirect(url_for("editor_visual_conteudo", id=id))

        with db() as conn:
            old = conn.execute("SELECT * FROM conteudos WHERE id=?", (id,)).fetchone()
            if not old:
                abort(404)

            # Salva versão anterior antes de alterar
            conn.execute("""
                INSERT INTO versoes(conteudo_id,titulo,descricao,html,tags,salvo_por,salvo_em)
                VALUES(?,?,?,?,?,?,?)
            """, (id, old["titulo"], old["descricao"], old["html"], old["tags"], current_user()["nome"], now()))

            conn.execute("""
                UPDATE conteudos
                SET titulo=?, html=?, atualizado_por=?, atualizado_em=?
                WHERE id=?
            """, (titulo, html, current_user()["nome"], today(), id))
            conn.commit()

        flash("Documento editado e salvo com sucesso.", "success")
        return redirect(url_for("abrir_anexo", id=id))

    with db() as conn:
        conteudo = conn.execute("""
            SELECT c.*, p.nome pasta_nome, s.nome setor_nome
            FROM conteudos c
            JOIN pastas p ON p.id=c.pasta_id
            JOIN setores s ON s.id=p.setor_id
            WHERE c.id=?
        """, (id,)).fetchone()

    if not conteudo:
        abort(404)

    return render_template("editor_documento.html", conteudo=conteudo)


@app.route("/admin/logs")
@login_required
@permission_required("ver_logs")
def logs():
    with db() as conn:
        itens = conn.execute("SELECT logs.*, usuarios.nome usuario_nome FROM logs LEFT JOIN usuarios ON usuarios.id=logs.usuario_id ORDER BY logs.id DESC LIMIT 300").fetchall()
    return render_template("logs.html", logs=itens)

@app.route("/admin/upload-imagem", methods=["POST"])
@login_required
@permission_required("upload_imagem")
def upload_imagem():
    img = request.files.get("imagem")
    if not img or not img.filename or not allowed(img.filename, IMG_EXT):
        flash("Envie uma imagem válida.", "danger"); return redirect(request.referrer or url_for("admin"))
    fname = secure_filename(datetime.now().strftime("%Y%m%d%H%M%S_") + img.filename)
    img.save(os.path.join(UPLOAD_IMG, fname))
    flash(f"Imagem enviada. Caminho: /uploads/imagens/{fname}", "success")
    return redirect(request.referrer or url_for("admin"))

@app.route("/admin/backup")
@login_required
@permission_required("gerar_backup")
def backup():
    fname = f"backup_portal_erasmo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    path = os.path.join(BACKUP_DIR, fname)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.exists(DB_PATH):
            z.write(DB_PATH, "database.db")
        for folder, label in [(UPLOAD_IMG, "uploads/imagens"), (UPLOAD_WORD, "uploads/word")]:
            for rootdir, dirs, files in os.walk(folder):
                for f in files:
                    full = os.path.join(rootdir, f)
                    rel = os.path.relpath(full, folder)
                    z.write(full, os.path.join(label, rel))
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
