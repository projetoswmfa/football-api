# 🚨 SOLUÇÃO: Erro "ECONNREFUSED" no n8n

## ❌ **O PROBLEMA**
```
Error: ECONNREFUSED
Full message: connect ECONNREFUSED ::1:8000
```

**Causa:** A API não está rodando no localhost:8000

---

## ✅ **SOLUÇÃO: INICIAR A API**

### 📋 **Pré-requisitos**
- Python 3.8 ou superior instalado
- Todas as dependências instaladas (`pip install -r requirements.txt`)

### 🚀 **Método 1: Usar o arquivo INICIAR_API.bat**
1. Execute o arquivo `INICIAR_API.bat` com duplo clique
2. Mantenha a janela aberta enquanto usa o n8n
3. Você verá a mensagem "Uvicorn running on http://127.0.0.1:8000"

### 🚀 **Método 2: Via linha de comando**
```bash
# Na pasta da API
python main.py
```

### 🚀 **Método 3: Usando o start_backend.bat**
```bash
# Este arquivo usa main_basic.py em vez de main.py
start_backend.bat
```

---

## ✅ **VERIFICAR SE A API ESTÁ RODANDO**

### 📊 **Teste 1: Acessar no navegador**
Abra: [http://localhost:8000](http://localhost:8000)

Você deve ver:
```json
{
  "message": "Sports Data API está funcionando!",
  "data": {
    "version": "1.0",
    "timestamp": "2024-07-01T10:30:24.997"
  }
}
```

### 📊 **Teste 2: Verificar partidas ao vivo**
Abra: [http://localhost:8000/matches/live](http://localhost:8000/matches/live)

Você deve ver uma lista de partidas ou um array vazio.

---

## 🔄 **FLUXO COMPLETO**

1. **INICIAR A API:**
   - Execute `INICIAR_API.bat` ou `python main.py`
   - Mantenha a janela aberta

2. **VERIFICAR SE ESTÁ FUNCIONANDO:**
   - Acesse [http://localhost:8000](http://localhost:8000) no navegador
   - Confirme que você vê a mensagem "API está funcionando"

3. **INICIAR O N8N:**
   - Em outra janela, inicie o n8n
   - Importe o workflow `SINAIS_APOSTAS_WORKFLOWS_FUNCIONAL.json`
   - Configure o Chat ID do Telegram
   - Ative o workflow

4. **TESTAR O WORKFLOW:**
   - No n8n, execute o workflow manualmente
   - Verifique se não há erros ECONNREFUSED

---

## ⚠️ **IMPORTANTE**

- **A API e o n8n devem rodar simultaneamente**
- **Mantenha a janela da API aberta o tempo todo**
- **Se fechar a API, o n8n não conseguirá se conectar**
- **Se reiniciar o computador, inicie a API novamente**

---

## 🔍 **DIAGNÓSTICO DE PROBLEMAS**

| Erro | Causa | Solução |
|------|-------|---------|
| `ECONNREFUSED` | API não está rodando | Iniciar a API com `INICIAR_API.bat` |
| `Invalid URL` | Variável de ambiente não configurada | Usar o workflow FUNCIONAL com URLs diretas |
| `404 Not Found` | Endpoint não existe | Verificar URL no workflow |
| `500 Internal Server Error` | Erro na API | Verificar logs da API |

---

## 🎯 **RESUMO**

1. ✅ **Iniciar API** (`INICIAR_API.bat`)
2. ✅ **Verificar** (abrir [http://localhost:8000](http://localhost:8000))
3. ✅ **Iniciar n8n** (em outra janela)
4. ✅ **Importar workflow** (`SINAIS_APOSTAS_WORKFLOWS_FUNCIONAL.json`)
5. ✅ **Configurar Telegram** (alterar Chat ID)
6. ✅ **Ativar workflow**

**Pronto! Sistema 100% funcional!** 🚀 