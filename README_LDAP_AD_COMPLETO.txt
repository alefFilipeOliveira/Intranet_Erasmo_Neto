GUIA DE ATIVAÇÃO LDAP / ACTIVE DIRECTORY
Portal Alef / Portal Erasmo

============================================================
OBJETIVO
============================================================

Este pacote já está pronto para usar LDAP/Active Directory.

Você só precisa preencher o arquivo:

ldap_config.py

Depois testar com:

teste_ldap.py

E então ativar:

LDAP_ENABLED = True


============================================================
USUÁRIOS DE EMERGÊNCIA
============================================================

Mesmo com LDAP ativado, estes usuários continuam locais:

usuario: val
senha: Erasmo@Adm2026

usuario: alef
senha: Alef@2026

Use eles se:
- o domínio cair;
- o AD ficar indisponível;
- a configuração LDAP estiver errada;
- você precisar entrar para corrigir algo.


============================================================
ARQUIVOS IMPORTANTES
============================================================

app.py
- Código principal.
- Já contém a lógica LDAP pronta.

ldap_config.py
- Arquivo onde você coloca as informações reais do AD.

teste_ldap.py
- Testa a conexão LDAP antes de ativar no portal.

requirements.txt
- Tem as dependências do projeto.
- Inclui ldap3.

README_LDAP_AD_COMPLETO.txt
- Este guia.


============================================================
DEPENDÊNCIA
============================================================

Ative o ambiente virtual:

.\venv\Scripts\Activate.ps1

Instale dependências:

python -m pip install -r requirements.txt

Teste se ldap3 está instalado:

python -c "import ldap3; print('LDAP OK')"


============================================================
PASSO 1 - PEGAR INFORMAÇÕES DO DOMÍNIO
============================================================

No servidor ou máquina com RSAT, rode:

Get-ADDomain

Anote:

DNSRoot
DistinguishedName
NetBIOSName

Exemplo:

DNSRoot: clinicaserasmoneto.local
DistinguishedName: DC=clinicaserasmoneto,DC=local
NetBIOSName: ERASMO

No ldap_config.py ficaria:

LDAP_DOMAIN = "ERASMO"
LDAP_BASE_DN = "DC=clinicaserasmoneto,DC=local"


============================================================
PASSO 2 - DESCOBRIR O CONTROLADOR DE DOMÍNIO
============================================================

Rode:

Get-ADDomainController -Discover

ou:

nltest /dsgetdc:ERASMO

Você pode usar IP ou nome DNS.

Exemplo:

LDAP_SERVER = "10.10.10.10"

ou:

LDAP_SERVER = "dc01.clinicaserasmoneto.local"


============================================================
PASSO 3 - CRIAR CONTA DE SERVIÇO
============================================================

Crie um usuário no AD, por exemplo:

svc_intranet

Essa conta não precisa ser Domain Admin.
Ela só precisa consultar usuários e grupos.

No ldap_config.py:

LDAP_BIND_USER = "ERASMO\\svc_intranet"
LDAP_BIND_PASSWORD = "SENHA_DA_CONTA"


============================================================
PASSO 4 - CRIAR GRUPOS DA INTRANET NO AD
============================================================

Grupos recomendados:

Intranet_Admin
Intranet_Marcacao
Intranet_Faturamento
Intranet_Financeiro
Intranet_Apoio
Intranet_Recepcao
Intranet_Conferencia

No PowerShell AD:

New-ADGroup -Name "Intranet_Admin" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Marcacao" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Faturamento" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Financeiro" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Apoio" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Recepcao" -GroupScope Global -GroupCategory Security
New-ADGroup -Name "Intranet_Conferencia" -GroupScope Global -GroupCategory Security


============================================================
PASSO 5 - COLOCAR USUÁRIOS NOS GRUPOS
============================================================

Exemplo:

Add-ADGroupMember -Identity "Intranet_Recepcao" -Members "maria.silva"
Add-ADGroupMember -Identity "Intranet_Admin" -Members "val"

Cada funcionário deve estar no grupo do setor dele.


============================================================
PASSO 6 - EDITAR ldap_config.py
============================================================

Abra:

ldap_config.py

Preencha:

LDAP_SERVER
LDAP_DOMAIN
LDAP_BASE_DN
LDAP_BIND_USER
LDAP_BIND_PASSWORD

Confira os grupos:

LDAP_ADMIN_GROUPS
LDAP_SETOR_GROUPS

Mantenha:

LDAP_ENABLED = False

até testar.


============================================================
PASSO 7 - TESTAR LDAP
============================================================

Rode:

python teste_ldap.py

Digite um usuário e senha reais do domínio.

O teste deve mostrar:

- conta de serviço OK;
- usuário encontrado;
- senha validada;
- grupos listados;
- setor encontrado, se o usuário estiver em grupo da intranet.


============================================================
PASSO 8 - ATIVAR LDAP NO PORTAL
============================================================

Quando o teste estiver OK, edite:

ldap_config.py

Troque:

LDAP_ENABLED = False

para:

LDAP_ENABLED = True

Reinicie o portal:

python -m waitress --host=0.0.0.0 --port=5000 app:app


============================================================
COMO O LOGIN FUNCIONA
============================================================

Se usuário for val ou alef:
- login local pelo SQLite.

Se LDAP_ENABLED = True:
- autentica no Active Directory;
- cria/atualiza o usuário no banco local;
- define perfil e setor pelos grupos do AD.

Se LDAP_ENABLED = False:
- usa login local antigo.


============================================================
MAPEAMENTO DE SETORES
============================================================

No ldap_config.py:

LDAP_SETOR_GROUPS = {
    "marcacao": ["Intranet_Marcacao"],
    "faturamento": ["Intranet_Faturamento"],
    "financeiro": ["Intranet_Financeiro"],
    "apoio": ["Intranet_Apoio"],
    "recepcao": ["Intranet_Recepcao"],
    "conferencia": ["Intranet_Conferencia"]
}

Não altere os slugs da esquerda se os setores já existem no banco.


============================================================
PERMISSÕES EXTRAS
============================================================

Você pode controlar permissões pelo painel ADM ou por grupos do AD.

Permissões possíveis:

anexar_documentos
editar_documentos
excluir_documentos
criar_pastas
editar_pastas
excluir_pastas
criar_avisos
editar_avisos
excluir_avisos
ver_lixeira
restaurar_lixeira
gerenciar_usuarios
gerar_backup
ver_logs
upload_imagem

Para usar AD, configure em:

LDAP_PERMISSION_GROUPS


============================================================
RECOMENDAÇÃO DE SEGURANÇA
============================================================

Para começar, use porta 389:

LDAP_PORT = 389
LDAP_USE_SSL = False

Depois que tudo funcionar, o ideal é migrar para LDAPS:

LDAP_PORT = 636
LDAP_USE_SSL = True

Isso exige certificado válido no controlador de domínio.


============================================================
CHECKLIST FINAL
============================================================

[ ] Instalar ldap3
[ ] Preencher ldap_config.py
[ ] Criar svc_intranet
[ ] Criar grupos Intranet_*
[ ] Colocar usuários nos grupos
[ ] Rodar python teste_ldap.py
[ ] Confirmar usuário encontrado e senha validada
[ ] Ativar LDAP_ENABLED = True
[ ] Reiniciar o portal
[ ] Testar login com usuário do domínio
[ ] Testar login local val
[ ] Testar login local alef
