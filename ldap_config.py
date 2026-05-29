# ============================================================
# PORTAL ALEF / PORTAL ERASMO
# CONFIGURAÇÃO LDAP / ACTIVE DIRECTORY
# ============================================================
#
# Este arquivo é o ÚNICO lugar onde você precisa colocar
# as informações reais do domínio da clínica.
#
# Enquanto LDAP_ENABLED estiver False, o sistema usa login local.
# Quando estiver True, usuários comuns entram pelo AD/Windows.
#
# Usuários locais de emergência que continuam funcionando:
# - val  / Erasmo@Adm2026
# - alef / Alef@2026
#
# ============================================================


# ============================================================
# 1. ATIVAR OU DESATIVAR LDAP
# ============================================================
# False = LDAP desligado. O sistema usa login local.
# True  = LDAP ligado. Funcionários usam usuário/senha do Windows.
LDAP_ENABLED = False


# ============================================================
# 2. SERVIDOR DO ACTIVE DIRECTORY
# ============================================================
# Coloque aqui o IP ou nome DNS do controlador de domínio.
#
# Exemplos:
# LDAP_SERVER = "10.10.10.10"
# LDAP_SERVER = "dc01.clinicaserasmoneto.local"
LDAP_SERVER = "10.10.10.X"


# Porta:
# 389 = LDAP normal
# 636 = LDAPS seguro
LDAP_PORT = 389

# False para porta 389
# True para porta 636 com certificado LDAPS funcionando
LDAP_USE_SSL = False


# ============================================================
# 3. DOMÍNIO
# ============================================================
# Nome curto NetBIOS do domínio.
# Você descobre com:
# Get-ADDomain
#
# Exemplo:
# LDAP_DOMAIN = "ERASMO"
# LDAP_DOMAIN = "CLINICA"
LDAP_DOMAIN = "ERASMO"


# Base DN do domínio.
# Você descobre com:
# Get-ADDomain
#
# Campo normalmente chamado DistinguishedName.
#
# Exemplo para erasmo.local:
# LDAP_BASE_DN = "DC=erasmo,DC=local"
#
# Exemplo para clinicaserasmoneto.local:
# LDAP_BASE_DN = "DC=clinicaserasmoneto,DC=local"
LDAP_BASE_DN = "DC=erasmo,DC=local"


# ============================================================
# 4. CONTA DE SERVIÇO
# ============================================================
# Conta usada pela intranet para pesquisar usuários e grupos no AD.
#
# Recomendo criar no AD:
# usuário: svc_intranet
#
# Essa conta NÃO precisa ser admin do domínio.
# Normalmente usuário comum já consegue consultar AD.
#
# Formatos aceitos:
# LDAP_BIND_USER = "ERASMO\\svc_intranet"
# LDAP_BIND_USER = "svc_intranet@erasmo.local"
LDAP_BIND_USER = "ERASMO\\svc_intranet"

# Senha da conta de serviço.
LDAP_BIND_PASSWORD = "COLOQUE_A_SENHA_AQUI"


# ============================================================
# 5. FILTRO DE BUSCA DO USUÁRIO
# ============================================================
# Para Active Directory, geralmente é sAMAccountName.
# Isso permite login como:
# joao.silva
#
# Se sua clínica usa UPN, pode adaptar depois.
LDAP_USER_SEARCH_FILTER = "(sAMAccountName={username})"


# ============================================================
# 6. ATRIBUTO DE GRUPOS
# ============================================================
# No Active Directory, memberOf lista os grupos do usuário.
LDAP_GROUP_ATTRIBUTE = "memberOf"


# ============================================================
# 7. GRUPO ADMINISTRADOR DA INTRANET
# ============================================================
# Quem estiver neste grupo entra como admin.
#
# Você pode colocar:
# - nome simples do grupo: "Intranet_Admin"
# - ou DN completo:
#   "CN=Intranet_Admin,OU=Grupos,DC=erasmo,DC=local"
#
# Nome simples costuma funcionar porque o sistema compara por trecho.
LDAP_ADMIN_GROUPS = [
    "Intranet_Admin"
]


# ============================================================
# 8. GRUPOS DE SETOR
# ============================================================
# Aqui você liga grupos do AD aos setores da intranet.
#
# O texto da esquerda é o slug do setor no sistema.
# Não altere os slugs se os setores já existem:
# - marcacao
# - faturamento
# - financeiro
# - apoio
# - recepcao
# - conferencia
#
# O texto da direita é o grupo do AD.
#
# Exemplo:
# Se Maria estiver no grupo Intranet_Recepcao,
# ela entrará automaticamente no setor Recepção.
LDAP_SETOR_GROUPS = {
    "marcacao": ["Intranet_Marcacao"],
    "faturamento": ["Intranet_Faturamento"],
    "financeiro": ["Intranet_Financeiro"],
    "apoio": ["Intranet_Apoio"],
    "recepcao": ["Intranet_Recepcao"],
    "conferencia": ["Intranet_Conferencia"]
}


# ============================================================
# 9. GRUPOS DE PERMISSÕES EXTRAS
# ============================================================
# Opcional.
#
# Se quiser controlar permissões pelo AD, crie grupos como:
# - Intranet_Anexar_Documentos
# - Intranet_Editar_Documentos
# - Intranet_Backup
#
# Se não quiser usar isso agora, pode deixar como está.
# Você ainda poderá controlar funções pelo painel ADM.
LDAP_PERMISSION_GROUPS = {
    "anexar_documentos": ["Intranet_Anexar_Documentos"],
    "editar_documentos": ["Intranet_Editar_Documentos"],
    "excluir_documentos": ["Intranet_Excluir_Documentos"],

    "criar_pastas": ["Intranet_Criar_Pastas"],
    "editar_pastas": ["Intranet_Editar_Pastas"],
    "excluir_pastas": ["Intranet_Excluir_Pastas"],

    "criar_avisos": ["Intranet_Criar_Avisos"],
    "editar_avisos": ["Intranet_Editar_Avisos"],
    "excluir_avisos": ["Intranet_Excluir_Avisos"],

    "ver_lixeira": ["Intranet_Lixeira"],
    "restaurar_lixeira": ["Intranet_Restaurar_Lixeira"],

    "gerenciar_usuarios": ["Intranet_Gerenciar_Usuarios"],
    "gerar_backup": ["Intranet_Backup"],
    "ver_logs": ["Intranet_Logs"],
    "upload_imagem": ["Intranet_Upload_Imagem"]
}


# ============================================================
# 10. CHECKLIST RÁPIDO
# ============================================================
#
# Para ativar:
#
# 1. Preencha:
#    LDAP_SERVER
#    LDAP_DOMAIN
#    LDAP_BASE_DN
#    LDAP_BIND_USER
#    LDAP_BIND_PASSWORD
#
# 2. Crie os grupos no AD:
#    Intranet_Admin
#    Intranet_Marcacao
#    Intranet_Faturamento
#    Intranet_Financeiro
#    Intranet_Apoio
#    Intranet_Recepcao
#    Intranet_Conferencia
#
# 3. Coloque os usuários dentro dos grupos.
#
# 4. Teste com:
#    python teste_ldap.py
#
# 5. Se funcionar, altere:
#    LDAP_ENABLED = True
#
# 6. Reinicie o portal.
# ============================================================
