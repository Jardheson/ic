# Mapa Técnico: IDs e Campos da Automação CNI

> **Fonte primária:** Extração VERBATIM de 9 imagens Chrome DevTools do DOM PrimeFaces (2026-09-15). Todos IDs confirmados no HTML real renderizado.

---

## 1. Formulário Principal

| Formulário | ID HTML | Observação |
|---|---|---|
| Parâmetros Pesquisa | `selectForm` | Contém 5 filtros + Estrato + 15 Variáveis + 3 Grupos de Rádio + Botão Pesquisar |
| Resultados Datatable | `listDifusaoLinhaForm` | Renderizado após clique em Pesquisar (abaixo na mesma página) |

---

## 2. 5 Filtros Básicos (FASE 3.0)

| Campo | Tipo | ID HTML (By.ID) | Valor Padrão |
|---|---|---|---|
| **Coorte** | SelectOneMenu | `selectForm:coorte` | `634` |
| **Mês Início** | SelectOneMenu | `selectForm:mesInicio` | `5` (maio) |
| **Ano Início** | SelectOneMenu | `selectForm:anoInicio` | `2026` |
| **Mês Fim** | SelectOneMenu | `selectForm:mesFim` | `7` (julho) |
| **Ano Fim** | SelectOneMenu | `selectForm:anoFim` | `2026` |

**Ordem obrigatória:** `Coorte → Mês Início → Ano Início → Mês Fim → Ano Fim` (mantém AJAX dependente).

---

## 3. Campo Estrato (FASE 3.2)

**Sempre executar ANTES de Variáveis (AJAX carrega opções de Variáveis!).**

| Atributo | Valor |
|---|---|
| Tipo widget | `SelectCheckboxMenu` PrimeFaces MULTISELECT |
| ID base widget | `selectForm:extrato` |
| Modo seleção | `preferencia` (5 labels preferidas), fallback `todas` |
| Values reais checkbox | `-1`, `161`, `162`, `163` (4 opções confirmadas) |
| Labels preferenciais padrão | `ESTRATO_PREFERENCIA_LABELS` em [constants.py](file:///g:/ic/config/constants.py) |

---

## 4. 15 Variáveis / Indicadores (FASE 3.1)

> **Fonte de verdade VISUAL:** tokens `<li class="ui-selectcheckboxmenu-token">` com `data-item-value` no widget.
> A automação aplica **interseção defaults ↔ valores desejados** e valida **tokens pós-fechamento** (2 tentativas de remarque forcado).

| Código Interno | Value REAL Checkbox (getAttribute) | Nome Indicador (Painel Variáveis) |
|---|---|---|
| p1  | **`948`** | Volume de Produção |
| p1t | **`955`** | Margem de Preços |
| p10 | **`969`** | Quantidade Exportada |
| p11 | **`970`** | Intenção de Investimento |
| p2  | **`961`** | UCI Usual |
| p2t | **`956`** | Situação Financeira |
| p3  | **`962`** | UCI (%) |
| p3t | **`957`** | Acesso a Crédito |
| p4  | **`963`** | Evolução Número de Empregados |
| p4t | **`958`** | Preço da Matéria-prima |
| p5  | **`965`** | Estoques Planejados |
| p6  | **`966`** | Evolução Estoques |
| p7  | **`964`** | Demanda / Nível de Pedidos |
| p8  | **`967`** | Número de Empregados Atual |
| p9  | **`968`** | Volume de Compras |

### 4.1 Detalhes Técnicos Widget Variáveis

| Atributo | Valor |
|---|---|
| Tipo | `SelectCheckboxMenu` MULTISELECT (`<div id="selectForm:variavel" class="ui-selectcheckboxmenu-multiple">`) |
| ID base | `selectForm:variavel` |
| Total checkboxes no painel | 31 inputs type=checkbox (inclui 16 de outras categorias) |
| Widget var JS | `PF('selectForm_variavelWidgetVar')` (opcional) |
| Fonte de verdade visual | `<ul class="ui-selectcheckboxmenu-token-container"><li class="ui-selectcheckboxmenu-token ui-state-active" data-item-value="XXXX">` |
| Modo seleção | (a) Interseção defaults ≥15 → pula marcação; (b) Senão → JS batch modo `lista_valores`; (c) Valida tokens pós-fechamento. |
| Mapeamento full 31 códigos | `VAR_COD_POR_VALUE` em [mappings.py](file:///g:/ic/domain/mappings.py) |

---

## 5. Grupos de Rádio (FASE 3.3 / 3.4)

### 5.1 Tipo de Estimativa

| Atributo | Valor |
|---|---|
| Table ID | `selectForm:tipoEstimativa` |
| Descoberta NAME real | Helper JS percorre todos inputs dentro da table (evita IDs dinâmicos PrimeFaces) |
| Value alvo padrão | `21` |

### 5.2 Exibição

| Atributo | Valor |
|---|---|
| Table ID | `selectForm:exibicao` |
| Característica PrimeFaces | Input dentro de `<div class="ui-helper-hidden-accessible">`; marcação visual via `div.ui-radiobutton-box.ui-state-active` |
| Value alvo padrão | `true` → Label "Valor" (e não "Variação") |

### 5.3 Orientação (NOVO, descoberto 2026-09-15)

| Atributo | Valor |
|---|---|
| Table ID | `selectForm:orientacao` |
| Values | `LINHA` ↔ `COLUNA` |
| Value alvo padrão | `LINHA` |

---

## 6. Botão Pesquisar

| Atributo | Valor |
|---|---|
| Tipo | `commandButton` PrimeFaces com AJAX submit |
| ID | `selectForm:pesquisar` (By.ID, substituindo XPath genérico anterior) |
| Espera pós-clique | Aguarda `listDifusaoLinhaForm:indicesVariavelDataTable` existir no DOM + pagina pronta overlay |

---

## 7. Datatable Resultados + Export Excel (FASE 4)

| Elemento | ID HTML | Observação |
|---|---|---|
| Datatable resultados | `listDifusaoLinhaForm:indicesVariavelDataTable` | Aparece abaixo do formulário; requer scroll na página |
| Footer DataTable (comandos paginação / exportação) | mesmo ID acima (footer é child) | Local do link Export Excel |
| **Link "Exportar para Excel"** | `listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140` | `<a title="Exportar resultados...">Exportar para excel</a> |

---

## 8. Ordem Absoluta de Preenchimento (NÃO INVERTER)

```
[FASE 3.0] Coorte
        → Mês Início
        → Ano Início
        → Mês Fim
        → Ano Fim
           ↓ AJAX concluído
[FASE 3.2] ESTRATO (SelectCheckboxMenu)
           ↓ AJAX obriga (carrega opções válidas de Variáveis!)
[FASE 3.1] VARIÁVEIS (15 da tabela acima)
           ↓ Widget já carregado
[FASE 3.3] RADIO Tipo Estimativa (value=21)
           ↓
[FASE 3.3] RADIO Exibição (value=true → "Valor")
           ↓
[FASE 3.4] RADIO Orientação (value=LINHA)
           ↓
[FASE 4]  Clica Botão Pesquisar
           ↓
[FASE 4]  Scroll + Aguarda Datatable visível
           ↓
[FASE 4]  Clica Exportar para Excel → Chrome baixa arquivo
```

---

## 9. Constantes Relacionadas no Código

| Constante | Arquivo |
|---|---|
| `LOCATOR_PARAM_COORTE_INPUT` / `_MES_INICIO` / `_ANO_INICIO` / `_MES_FIM` / `_ANO_FIM` | [constants.py](file:///g:/ic/config/constants.py) |
| `WIDGET_ESTRATO_BASE_ID = "selectForm:extrato"` | [constants.py](file:///g:/ic/config/constants.py) |
| `WIDGET_VARIAVEIS_BASE_ID = "selectForm:variavel"` | [constants.py](file:///g:/ic/config/constants.py) |
| `RADIO_TIPO_ESTIMATIVA_TABLE_ID = "selectForm:tipoEstimativa"` | [constants.py](file:///g:/ic/config/constants.py) |
| `RADIO_EXIBICAO_TABLE_ID = "selectForm:exibicao"` | [constants.py](file:///g:/ic/config/constants.py) |
| `RADIO_ORIENTACAO_TABLE_ID = "selectForm:orientacao"` | [constants.py](file:///g:/ic/config/constants.py) |
| `BTN_PESQUISAR_ID = "selectForm:pesquisar"` | [constants.py](file:///g:/ic/config/constants.py) |
| `DATATABLE_RESULTADOS_ID = "listDifusaoLinhaForm:indicesVariavelDataTable"` | [constants.py](file:///g:/ic/config/constants.py) |
| `EXPORT_EXCEL_LINK_ID = "listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140"` | [constants.py](file:///g:/ic/config/constants.py) |
| `DEFAULT_VARIAVEIS_CODIGOS` (15 códigos internos p1..p11) | [constants.py](file:///g:/ic/config/constants.py) |
| `codigos_para_values()` → converte códigos internos → values reais checkbox | [mappings.py](file:///g:/ic/domain/mappings.py) |
