PORTAL ALEF - LOGIN LDAP / ACTIVE DIRECTORY

Esta versão permite autenticação usando o domínio Windows da clínica.

O que muda:
- Funcionários entram com usuário e senha do Windows.
- A intranet consulta o Active Directory.
- O setor pode ser definido por grupo do AD.
- O admin pode ser definido por grupo do AD.
- Permissões extras podem vir de grupos do AD ou continuar sendo ajustadas no painel ADM.

Usuários locais de emergência:
- val
- alef

Mesmo com LDAP ligado, estes dois continuam usando o banco local.
Use eles caso o domínio esteja fora do ar.

LOGIN DE EMERGÊNCIA:
usuario: val
senha: Erasmo@Adm2026

usuario: alef
senha: Alef0405@


1. DEPENDÊNCIA NOVA

No requirements.txt foi adicionado:

ldap3==2.9.1

Instale com:

python -m pip install -r requirements.txt


2. ARQUIVO DE CONFIGURAÇÃO

Foi criado:

ldap_config.py

Você deve editar esse arquivo com os dados reais do domínio.


3. INFORMAÇÕES QUE O LEO PRECISA ACRESCENTAR 

domínio:

- IP ou nome do controlador de domínio
  Exemplo: 10.10.10.10 ou dc01.clinicas.local

- Nome do domínio NetBIOS
  Exemplo: CLINICA

- Base DN
  Exemplo: DC=clinica,DC=local

- Conta de serviço para consulta
  Exemplo: CLINICA\svc_intranet

- Senha da conta de serviço

- Nomes dos grupos do AD para os setores:
  Intranet_Marcacao
  Intranet_Faturamento
  Intranet_Financeiro
  Intranet_Apoio
  Intranet_Recepcao
  Intranet_Conferencia
  Intranet_Admin


4. COMO ATIVAR

No arquivo ldap_config.py, altere:

LDAP_ENABLED = False

para:

LDAP_ENABLED = True


5. GRUPOS RECOMENDADOS NO ACTIVE DIRECTORY

Crie estes grupos no AD:

- Intranet_Admin
- Intranet_Marcacao
- Intranet_Faturamento
- Intranet_Financeiro
- Intranet_Apoio
- Intranet_Recepcao
- Intranet_Conferencia

Opcional para permissões finas:
- Intranet_Anexar_Documentos
- Intranet_Editar_Documentos
- Intranet_Excluir_Documentos
- Intranet_Criar_Pastas
- Intranet_Criar_Avisos
- Intranet_Backup
- Intranet_Logs


6. COMO FUNCIONA O LOGIN

Se o usuário for val ou alef:
- autentica localmente pelo banco SQLite.

Se LDAP_ENABLED = True:
- autentica no Active Directory.
- se der certo, cria/atualiza o usuário local automaticamente.
- define setor e perfil pelos grupos do AD.

Se LDAP_ENABLED = False:
- continua usando login local antigo.


7. IMPORTANTE

O banco SQLite continua sendo usado para:
- setores;
- pastas;
- anexos;
- avisos;
- permissões manuais;
- temas;
- logs;
- backups;

O Active Directory cuida da senha e da autenticação dos funcionários.
