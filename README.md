# Pata & Companhia — Pet Shop para aulas de QA

Aplicação Flask em português com catálogo, busca, filtro por categoria, carrinho,
edição de quantidades, remoção e finalização simulada. Interface responsiva,
valores em centavos e formulários com proteção CSRF.

Não processa pagamentos nem mantém pedidos ou estoque. O catálogo é fixo e o
carrinho fica em cookie de sessão assinado, sem dados pessoais. Em produção,
`SECRET_KEY` deve ser estável e secreta. Localmente uma chave temporária é gerada
a cada inicialização; reiniciar invalida sessões anteriores.

## Executar localmente (Windows / PowerShell)

Instale Python 3.12 e confirme `python --version`. Se usar o launcher do Windows,
substitua o primeiro `python` por `py -3.12`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app app run
```

Abra http://127.0.0.1:5000. Encerre com Ctrl+C. Não é necessário ativar o ambiente
virtual nem alterar a política do PowerShell. Em Linux/macOS use `.venv/bin/python`.

Nesta máquina foi preparado um Python portátil em `.tools/portable`, pois o
comando `python` do Windows não estava funcional. Ele e suas dependências estão
ignorados pelo Git. Para executar imediatamente neste checkout:

```powershell
.\.tools\portable\python.exe -m flask --app app run
```

Esse ambiente local não é enviado ao GitHub; em outras máquinas siga a instalação
com `.venv` descrita acima.

## Executar testes

```powershell
.\.venv\Scripts\python.exe -m pytest -v --junitxml=test-results.xml --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=90
```

Os testes usam o cliente HTTP do Flask, sem servidor real nem conexão externa.
Cada teste recebe uma aplicação e sessão novas. O fixture `post` obtém um token
CSRF válido, preservando a proteção também nos testes.

Os cenários cobrem catálogo, pesquisa, categorias, HTML escapado, carrinho vazio,
adição acumulada, totais de vários produtos, edição, remoção, limite de unidades,
quantidades inválidas, produto inexistente, isolamento de sessões, CSRF, checkout,
métodos HTTP, health check e cookies do Render. São testes do backend: não
substituem testes de navegador, acessibilidade ou carga. Inspecione também a loja
em tela estreita e com Tab e complete o fluxo catálogo → carrinho → finalizar.

Validação local em 22/10/2026: **35 testes passaram**, com **100% de cobertura de
linhas de `app.py`**, usando Python 3.12.8. Não houve validação visual em navegador,
execução remota do GitHub Actions ou deploy. Para repetir neste checkout:

```powershell
.\.tools\portable\python.exe -m pytest -v --junitxml=test-results.xml --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=90
```

## Estrutura

| Arquivo | Finalidade |
| --- | --- |
| `app.py` | Factory Flask, rotas, catálogo, sessão e validações |
| `templates/` e `static/style.css` | Interface e estilos |
| `tests/` | Fixtures e cenários Pytest |
| `requirements.txt` | Dependências de execução |
| `requirements-dev.txt` | Dependências de testes |
| `.github/workflows/ci.yml` | Integração contínua |
| `render.yaml` | Configuração de deploy |

## Pipeline CI, etapa por etapa

1. **Gatilhos (`on`)**: qualquer `push` ou `pull_request` inicia o workflow. Não há
   filtro de branches ou caminhos que pule os testes.
2. **Executor (`runs-on`)**: o GitHub cria uma máquina Linux limpa e temporária.
   O job `Pytest` tem limite de dez minutos e permissão de leitura do código.
3. **Checkout**: `actions/checkout` baixa o código da revisão avaliada.
4. **Python**: `actions/setup-python` seleciona Python 3.12 e configura cache do
   pip com base nos arquivos de requisitos. O cache não substitui a instalação.
5. **Dependências**: pip instala Flask, Gunicorn no Linux, Pytest e pytest-cov.
6. **Testes e cobertura**: qualquer teste com falha retorna código diferente de
   zero e deixa o job vermelho. Cobertura abaixo de 90% também reprova. Os logs
   mostram linhas não cobertas; os XMLs de cobertura e JUnit ficam no runner,
   sem upload de artefatos nesta versão.
7. **Resultado**: a aba Actions exibe os logs de cada etapa. A PR recebe o check
   `Pytest`. Para impedir merges com falhas, configure uma regra de proteção da
   branch exigindo esse check; o YAML não configura essa regra.

O job de testes continua separado do job de deploy. O nome do check de testes
permanece `Pytest`, para manter a referência em regras de proteção já configuradas.
Referência: https://docs.github.com/en/actions/tutorials/build-and-test-code/python

## CI e CD separados no GitHub Actions

O arquivo `.github/workflows/ci.yml` contém dois jobs. No gráfico do Actions:

```text
Pytest (CI) → CD - Render
```

`needs: tests` faz o CD aguardar o CI e impede deploy quando os testes falham.
Em pull requests e pushes em outras branches, apenas CI executa; CD fica ignorado.
Um push em `release/homolog` seleciona o Environment `homologacao`; em `main`,
seleciona `producao`. O CD envia ao Render o SHA do commit aprovado, usando um
Deploy Hook. O job verde significa que o Render aceitou a solicitação, não que a
publicação terminou. Build, inicialização e health check são acompanhados no Render.

### Configuração necessária (após autorização para publicação)

1. Crie dois serviços Render: produção com `render.yaml` na branch `main` e
   homologação com `render-homolog.yaml` na branch `release/homolog`.
2. Em cada serviço, confirme **Settings → Auto-Deploy → Off**. Ambos os YAMLs
   usam `autoDeployTrigger: 'off'` para deixar o deploy de código a cargo do Actions.
   A criação inicial e sincronizações do Blueprint podem provisionar ou atualizar
   recursos; revise essas operações separadamente no Render.
3. No GitHub, abra **Settings → Environments** e crie `homologacao` e `producao`.
4. Em cada Environment, adicione um **Environment secret** chamado
   `RENDER_DEPLOY_HOOK_URL`. O valor deve ser a URL de **Settings → Deploy Hook**
   do serviço Render correspondente. Use o mesmo nome de secret nos dois ambientes,
   com valores diferentes. Não coloque a URL em código, logs ou mensagens.
5. Quando disponíveis para seu plano/repositório, restrinja as branches permitidas
   de cada Environment e configure aprovação manual para `producao` se desejar.
6. Depois de revisar e autorizar o envio, um push em cada branch executará CI e
   acionará somente seu serviço. Sem o secret, CI pode passar, mas CD falha com
   uma mensagem de configuração. Não foi realizada nenhuma configuração remota.

Referências: https://render.com/docs/deploy-hooks e
https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments

## Deploy no Render e ligação com o CI

**O projeto permanece local.** Execute este procedimento somente após autorizar
o envio ao GitHub e a criação do serviço no Render.

1. Envie o projeto revisado para um repositório GitHub. O Blueprint assume a branch
   `main`; ajuste `branch` se usar outro nome.
2. Conecte sua conta GitHub ao Render. Escolha **New → Blueprint**, selecione o
   repositório e use `render.yaml`. Revise plano e condições antes de confirmar.
3. O Render instala `requirements.txt` e inicia `gunicorn app:app`, ouvindo em
   `0.0.0.0:$PORT`. Gunicorn é o servidor de produção; `flask run` é para uso local.
4. O Blueprint gera `SECRET_KEY`, fixa Python 3.12.8 e usa `/health` para verificar
   a saúde. Não coloque segredos no repositório.
5. `autoDeployTrigger: 'off'` desativa o deploy automático por commit no Render.
   Configure os Environments e Deploy Hooks no GitHub conforme a seção acima.
   A criação inicial pelo Blueprint já provisiona o serviço: revise o resultado
   do CI antes de criá-lo. Não há previews de PRs.
6. Um push ou merge em `main` executa CI; passando os testes, o job CD chama o Render.
   Uma PR testa a proposta, mas só vai para produção após chegar à branch vinculada.
   Falhas de build ou health check ainda podem impedir deploy com CI verde:
   acompanhe os logs do Render.
7. Abra a URL fornecida pelo Render, consulte `/health` e valide a compra simulada.

O serviço gratuito pode suspender por inatividade e demorar ao iniciar; confirme
disponibilidade e limites no painel. Não há banco ou disco persistente. Carrinhos
continuam válidos entre reinícios enquanto a chave e o cookie forem válidos.
Fontes do Google são opcionais: a interface tem fontes locais de fallback.

Referências oficiais:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/deploys

## Roteiro para demonstrar CI/CD

1. Execute os testes localmente. Explique **arrange, act, assert** no teste de total:
   preparar produtos, enviar requisições e conferir o preço.
2. Após autorização para GitHub, crie uma branch de aula e altere propositalmente
   uma expectativa de total. Rode localmente e abra uma PR para mostrar CI vermelho.
3. Corrija a expectativa, rode novamente e envie a correção: o check fica verde.
4. Após revisão e autorização, faça merge. Mostre o CI em `main` e, se configurado,
   o deploy do Render depois dos checks.
5. **CI** integra e verifica o código. **CD** entrega a versão aprovada ao ambiente.
   Testes verdes comprovam os cenários exercitados, não ausência de todo defeito.
