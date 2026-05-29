"""
TESTE DE LDAP / ACTIVE DIRECTORY
Portal Alef / Portal Erasmo

Use este arquivo ANTES de ativar o LDAP no portal.

Como usar:

1. Edite o arquivo ldap_config.py com os dados reais.
2. Instale dependências:
   python -m pip install -r requirements.txt

3. Rode:
   python teste_ldap.py

4. Digite um usuário e senha do domínio para testar.

Se aparecer:
- usuário encontrado
- senha validada
- grupos listados

Então o LDAP está pronto para ser ativado no portal.
"""

from getpass import getpass
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import ldap_config as cfg


def normalizar_usuario(usuario):
    usuario = (usuario or "").strip()
    if "\\" in usuario:
        usuario = usuario.split("\\", 1)[1]
    if "@" in usuario:
        usuario = usuario.split("@", 1)[0]
    return usuario.lower()


def main():
    print("=" * 60)
    print("TESTE LDAP / ACTIVE DIRECTORY - PORTAL ALEF")
    print("=" * 60)
    print()

    print("Servidor:", cfg.LDAP_SERVER)
    print("Porta:", cfg.LDAP_PORT)
    print("SSL:", cfg.LDAP_USE_SSL)
    print("Domínio:", cfg.LDAP_DOMAIN)
    print("Base DN:", cfg.LDAP_BASE_DN)
    print()

    usuario_digitado = input("Usuário do domínio para teste: ").strip()
    senha_digitada = getpass("Senha do usuário de teste: ")

    username = normalizar_usuario(usuario_digitado)

    print()
    print("Conectando no servidor LDAP...")

    server = Server(
        cfg.LDAP_SERVER,
        port=int(cfg.LDAP_PORT),
        use_ssl=bool(cfg.LDAP_USE_SSL),
        get_info=ALL
    )

    print("Fazendo bind com conta de serviço...")

    conn = Connection(
        server,
        user=cfg.LDAP_BIND_USER,
        password=cfg.LDAP_BIND_PASSWORD,
        authentication=NTLM,
        auto_bind=True
    )

    print("Conta de serviço OK.")
    print("Buscando usuário:", username)

    search_filter = cfg.LDAP_USER_SEARCH_FILTER.format(username=username)

    conn.search(
        cfg.LDAP_BASE_DN,
        search_filter,
        search_scope=SUBTREE,
        attributes=["cn", "displayName", "mail", "memberOf", "sAMAccountName"]
    )

    if not conn.entries:
        print()
        print("ERRO: usuário não encontrado no AD.")
        conn.unbind()
        return

    entry = conn.entries[0]

    print()
    print("Usuário encontrado:")
    print("DN:", entry.entry_dn)

    if hasattr(entry, "displayName"):
        print("Nome:", entry.displayName)

    if hasattr(entry, "mail"):
        print("E-mail:", entry.mail)

    print()
    print("Validando senha do usuário...")

    user_login = f"{cfg.LDAP_DOMAIN}\\{username}"

    test_conn = Connection(
        server,
        user=user_login,
        password=senha_digitada,
        authentication=NTLM,
        auto_bind=True
    )

    print("Senha validada com sucesso.")

    print()
    print("Grupos do usuário:")
    grupos = []
    if hasattr(entry, "memberOf"):
        try:
            grupos = [str(g) for g in entry.memberOf.values]
        except Exception:
            grupos = []

    if grupos:
        for grupo in grupos:
            print("-", grupo)
    else:
        print("Nenhum grupo retornado em memberOf.")

    print()
    print("Verificação de grupos da intranet:")

    todos_grupos_lower = [g.lower() for g in grupos]

    def pertence(grupos_config):
        for grupo_config in grupos_config:
            grupo_config = str(grupo_config).lower()
            for grupo_usuario in todos_grupos_lower:
                if grupo_config == grupo_usuario or grupo_config in grupo_usuario:
                    return True
        return False

    print("Admin:", pertence(cfg.LDAP_ADMIN_GROUPS))

    for setor, grupos_setor in cfg.LDAP_SETOR_GROUPS.items():
        if pertence(grupos_setor):
            print("Setor encontrado:", setor)

    print()
    print("TESTE FINALIZADO COM SUCESSO.")
    print("Se o setor e/ou admin apareceram corretamente, pode ativar LDAP_ENABLED = True.")

    test_conn.unbind()
    conn.unbind()


if __name__ == "__main__":
    main()