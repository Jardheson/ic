# Plano: Documentação Completa do Projeto + Limpeza de Arquivos Desnecessários

## 1. Repository Research (Inventário Atual)

### 1.1 Arquitetura do Projeto (7 camadas confirmadas)
```
g:\ic\
├── config/              → settings.py (Pydantic .env), constants.py (IDs mapeados)
├── core/                → errors.py, retry.py (backoff), security.py (6 pilares), lock.py (single-instance)
├── domain/              → models.py (PesquisaParams frozen), validators.py, mappings.py (VAR_COD_POR_VALUE)
├── infrastructure/
│   └── browser/         → driver.py (Chrome custom), waits.py (passo/polling), actions.py (JS batch, radio, checkbox, navegação)
├── pages/ (POM)         → base_page.py, login_page.py, menu_page.py, parametros_page.py, resultados_page.py
├── services/            → auth_service.py, navigation_service.py, pesquisa_service.py (todos @with_retry ≥3)
├── tests/ (18 testes)   → test_core_errors.py, test_core_retry.py, test_domain_models.py
├── main.py              → entry point <200 linhas (Lock + Watchdog + Whitelist + Sanitize)
├── main_monolith_backup.py → backup 2900 linhas do código original (aberto no IDE agora)
├── .env / .env.example  → credenciais e template
├── requirements.txt     → dependências (selenium, pydantic, pytest, python-dotenv)
├── diag_sem_datatable.png → screenshot temporário de diagnóstico (antigo)
├── .pipeline.lock       → lock obsoleto de execução interrompida
├── .pytest_cache/       → cache pytest (sempre recriado)
└── __pycache__/ (vários)→ bytecode Python (sem valor em repositório)
```

### 1.2 IDs Técnicos Confirmados (100% do DOM via 9 imagens DevTools)
- Widgets: `selectForm:coorte`, `selectForm:mesInicio`, `selectForm:anoInicio`, `selectForm:mesFim`, `selectForm:anoFim`, `selectForm:extrato` (Estrato), `selectForm:variavel` (15 vars)
- Radios: `selectForm:tipoEstimativa`, `selectForm:exibicao`, `selectForm:orientacao` (NOVO)
- Botões: `selectForm:pesquisar` (Pesquisar)
- Resultados: `listDifusaoLinhaForm:indicesVariavelDataTable` + `listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140` (Export Excel)

### 1.3 15 Variáveis Mapeadas (códigos internos → values reais)
p1(948) p1t(955) p10(969) p11(970) p2(961) p2t(956) p3(962) p3t(957) p4(963) p4t(958) p5(965) p6(966) p7(964) p8(967) p9(968)

### 1.4 Lacunas de Documentação (0 arquivos .md existentes na raiz)
- NENHUM README / ARCHITECTURE / SECURITY / TESTING / CONTRIBUTING / CHANGELOG / DEPLOYMENT

### 1.5 Arquivos Desnecessários Identificados
| Arquivo / Pasta | Motivo | Ação |
|---|---|---|
| `.pipeline.lock` | Lock obsoleto de execução interrompida → SEMPRE deve ser removido após execução | EXCLUIR |
| `diag_sem_datatable.png` | Screenshot temporário diagnóstico de rodada anterior → nenhuma referência no código | EXCLUIR |
| `.pytest_cache/` | Cache pytest → recriado automaticamente em todo `pytest` | EXCLUIR pasta inteira |
| `**/__pycache__/*.pyc` | Bytecode Python compilado → sem valor em repositório | EXCLUIR todos (ja era removido manualmente, é garantia) |
| `main_monolith_backup.py` | Backup monólito original 2900 linhas (**ABERTO NO IDE PELO USUÁRIO**) | MANTER POR PADRÃO — usuário pode confirmar exclusão depois se quiser |
| `.trae/specs/refatoracao-arquitetural-cni/` | Spec Mode da refatoração anterior (já concluída). Artefato de planejamento. | MANTER por enquanto (histórico) |

---

## 2. Documentação a Criar (8 arquivos + pasta `docs/`)

| # | Arquivo | Conteúdo |
|---|---|---|
| 1 | `README.md` (raiz) | Visão geral, stack tecnológica, arquitetura em 1 linha, fluxo da automação, pré-requisitos (Python 3.12+, Chrome), instalação (venv + requirements), execução rápida (`python main.py`), estrutura de pastas resumida, solução de problemas comuns (credenciais, __pycache__, timeout). |
| 2 | `docs/ARCHITECTURE.md` | Clean Architecture 7 camadas explicadas em detalhe, responsabilidades de cada camada, dependências (SETAS: main → services → pages/domain/config/core; services NUNCA importam By/find_element), Injeção de Dependência, diagrama textual Mermaid das camadas, fluxo de dados pipeline (Fase0→Fase1→Fase2→Fase3→Fase4), Princípios SOLID aplicados, Hard Constraints (ordem rígida Fase3). |
| 3 | `docs/SECURITY.md` | 6 pilares SEG-1..SEG-6 implementados em detalhe: (1) Injeção JS arguments[0..N], (2) URL Whitelist (hosts permitidos), (3) Watchdog timeout global, (4) Sanitização logs regex keywords, (5) Permissões .env, (6) Lock single-instance. Inclui: como estender whitelist, como ajustar timeout, palavras-chave sensíveis da sanitização. |
| 4 | `docs/TESTING.md` | Pytest 18 testes atuais listados por arquivo (test_core_errors: 7; test_core_retry: 3; test_domain_models: 8). Como rodar: `pytest tests -v`, `pytest --cov`, como adicionar novo teste (estrutura, convenções), cobertura de validações Pydantic, testes de retry/backoff, testes negativos de validação. |
| 5 | `docs/DEPLOYMENT.md` | Variáveis de ambiente `.env` (CNI_USER, CNI_PASSWORD explícito sem valores), template `.env.example`, permissões .env (chmod 600 Linux / ACL Windows), forma de execução em ambiente produtivo (headless=True, chromedriver, logs), diagnóstico de erros mais frequentes e soluções (InvalidSelector → escape ::: TypeError passo() → limpar __pycache__; RetryableError variáveis → confirmar defaults). |
| 6 | `docs/AUTOMACAO_MAPA_CAMPOS.md` | Mapa TÉCNICO COMPLETO dos IDs PrimeFaces extraídos das 9 imagens DevTools: (a) 5 filtros básicos locators, (b) Estrato (SelectCheckboxMenu) values/labels, (c) 15 Variáveis (p1..p11) códigos + values reais, (d) Radios (TipoEstimativa/Exibição/Orientação) values e labels, (e) Datatable resultados + Export Excel ID, (f) Ordem de preenchimento obrigatória, (g) Modo seleção variáveis (interseção defaults + validação tokens). |
| 7 | `docs/CHANGELOG.md` | Histórico de versões/mudanças com data: (2026-09-15: Melhoria Variáveis + Segurança 6 pilares), (2026-09-15: Refatoração monólito → Clean Arch 7 camadas / 30 arquivos / 18 testes), padrão Conventional Commits. |
| 8 | `docs/CONTRIBUTING.md` | Padrões de código: SOLID, Clean Code, NÃO inventar, Page Object Model (locators privados By.ID), Services sem By/find_element, @with_retry≥3, PesquisaParams frozen, python-dotenv + Pydantic fail-fast. Padrão de commits (feat/fix/docs/refactor/test/chore). Fluxo: py_compile → pytest → rodar main.py. |

---

## 3. Passos de Implementação (Ordem de Dependência)

### Passo 1 — Limpeza Inicial (primeiro, para reduzir ruído)
1.1 Excluir `.pipeline.lock` (lock obsoleto).  
1.2 Excluir `diag_sem_datatable.png` (screenshot temporário).  
1.3 Excluir `.pytest_cache/` inteiro.  
1.4 Excluir todo `**/__pycache__/` recursivo (aplicar todos módulos).  

### Passo 2 — Criar pasta `docs/`
2.1 Criar diretório `g:\ic\docs\`.

### Passo 3 — Gerar os 8 documentos
**Ordem (menor para maior; já prepara referências cruzadas):**  
3.1 `README.md` (raiz, primeiro ponto de contato).  
3.2 `docs/AUTOMACAO_MAPA_CAMPOS.md` (dados técnicos extraídos do DOM).  
3.3 `docs/ARCHITECTURE.md` (camadas + fluxo).  
3.4 `docs/SECURITY.md` (6 pilares).  
3.5 `docs/TESTING.md` (pytest 18 testes).  
3.6 `docs/DEPLOYMENT.md` (.env + execução).  
3.7 `docs/CONTRIBUTING.md` (padrões código).  
3.8 `docs/CHANGELOG.md` (histórico).  

### Passo 4 — Validação
4.1 Verificar que todos 8 arquivos .md foram criados e são acessíveis.  
4.2 Verificar que `README.md` na raiz tem links para `docs/` correspondentes.  
4.3 Verificar que arquivos excluídos (Step1) não existem mais.  
4.4 Rodar `pytest tests/` para garantir que limpeza não quebrou nada.  
4.5 Rodar `python -m compileall -q g:\ic` (sem erros de sintaxe).  

---

## 4. Dependências e Considerações
- **main_monolith_backup.py**: Mantido por padrão (usuário abriu no IDE; é o backup do código original antes da refatoração). Se quiser excluir posteriormente é só confirmar.
- **.env / .env.example**: **NUNCA excluídos**, mantidos.
- **.venv/**: Jamais tocado (está em `.gitignore` se existir; ambiente virtual).
- **.trae/specs/**: Mantido como histórico de planejamentos anteriores já concluídos; pode ser limpo depois se não for mais referência.
- **Toda documentação em PORTUGUÊS BRASIL (pt-BR)**, igual mensagens do usuário e comentários no código.

---

## 5. Validação Pós-Execução
- [ ] 8 documentos .md criados com conteúdo real e não vazio.
- [ ] README.md tem links clicáveis para `docs/` (`file:///g:/ic/docs/...`).
- [ ] `.pipeline.lock` → excluído.
- [ ] `diag_sem_datatable.png` → excluído.
- [ ] `.pytest_cache/` → excluído.
- [ ] Nenhum `__pycache__/` restante em nenhuma das 7 camadas.
- [ ] `pytest tests -v` → 18 passed.
- [ ] `python -m py_compile main.py config constants settings core domain pages services tests infra` → exit 0.
- [ ] `main_monolith_backup.py` → PRESERVADO (conforme estratégia).

---

## 6. Riscos e Tratamento
| Risco | Prob | Impacto | Tratamento |
|---|---|---|---|
| Excluir arquivo necessário por engano | Baixa | Alto | Lista fechada no Step1; .env / .venv / backup monólito **nunca** são tocados. |
| Documentação ficar incompleta ou genérica | Média | Médio | Cada documento tem escopo FECHADO definido na tabela §2; cross-check com código real (constantes, mapeamentos, 18 testes). |
| Links entre docs quebrarem | Baixa | Baixo | Usar `file:///` caminho absoluto g:\ic\... + extensão .md correta. |
| Limpar __pycache__ de .venv | Média | Baixo | Glob filtrado: excluir somente `config/`, `core/`, `domain/`, `infrastructure/`, `pages/`, `services/`, `tests/` __pycache__ (jamais .venv). |
