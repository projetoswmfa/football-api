# 🔧 Como Importar o Workflow de Sinais de Apostas no n8n

## ✅ Problema Resolvido: Conexões entre Nós

**RESOLVIDO**: As conexões entre os nós estavam quebradas, mas agora foram corrigidas!

### 📊 Estrutura Atual do Workflow

**9 nós conectados em sequência:**

1. **A cada 5 minutos** (Cron) → 
2. **Buscar Partidas** (HTTP) → 
3. **Tem partidas?** (IF) → 
4. **Cada partida** (Split) → 
5. **Gerar Sinais IA** (HTTP) → 
6. **Filtrar Confiança** (Function) → 
7. **Tem sinais?** (IF) → 
8. **Formatar Mensagem** (Set) → 
9. **Enviar Telegram** (Telegram)

---

## 🚀 Passos para Importação

### 1. Preparar o n8n
```bash
# Abrir n8n
npx n8n
```

### 2. Importar o Workflow
1. No n8n, clique em **"+"** (Novo workflow)
2. Clique nos **3 pontinhos** (...) no canto superior direito
3. Selecione **"Import from JSON"**
4. Copie e cole o conteúdo do arquivo `SINAIS_APOSTAS_WORKFLOWS.json`
5. Clique em **"Import"**

### 3. Configurar Variáveis de Ambiente
```env
# No n8n, vá em Settings > Environment Variables
SPORTS_API_URL=http://localhost:8000
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
```

### 4. Configurar Credenciais do Telegram
1. Vá em **Credentials**
2. Crie uma nova credencial do tipo **"Telegram"**
3. Insira seu **Bot Token**
4. Salve as credenciais

### 5. Ativar o Workflow
1. Clique no botão **"Active"** no canto superior direito
2. O workflow começará a executar automaticamente a cada 5 minutos

---

## 🎯 Funcionamento do Sistema

### Fluxo Automático
- **A cada 5 minutos**: Sistema busca partidas ao vivo
- **Para cada partida**: Gera sinais de IA para escanteios, cartões e ambas marcam
- **Filtra apenas**: Sinais com confiança ≥ 7/10
- **Envia automaticamente**: Mensagens formatadas no Telegram

### Tipos de Sinais
- 🚨 **ESCANTEIO**: Previsões para total de escanteios
- 🟡 **CARTÃO**: Previsões para cartões amarelos/vermelhos  
- ⚽ **AMBAS MARCAM**: Previsões se ambos os times marcarão

### Mensagem de Exemplo
```
🤖 SINAIS AUTOMÁTICOS - ALTA CONFIANÇA

🚨 ESCANTEIO
CONFIANÇA: 8/10

Barcelona vs Real Madrid
Mais de 10.5 escanteios
Ambos os times têm média alta...

═══════════════

🟡 CARTÃO
CONFIANÇA: 7/10

Manchester City vs Arsenal
Mais de 3.5 cartões
Histórico de confrontos duros...

⏰ 14:35 - Análise IA Gemini
🎯 2 sinal(is) detectado(s)
```

---

## 🔧 Validação Técnica

✅ **JSON válido** - Sem erros de sintaxe  
✅ **9 nós configurados** - Workflow completo  
✅ **8 conexões funcionando** - Fluxo linear perfeito  
✅ **Encoding UTF-8** - Suporte completo a acentos  
✅ **Compatível n8n** - Testado e aprovado  

---

## ⚠️ Requisitos

### API Sports Data
- Sua API deve estar rodando em `http://localhost:8000`
- Endpoints `/matches/live` e `/betting/all-signals` funcionando
- Gemini IA configurada para análises

### Bot Telegram
- Bot criado via @BotFather
- Token obtido e configurado
- Chat ID do grupo/canal de destino

---

## 🎉 Pronto!

Seu sistema de sinais automáticos está funcionando! O workflow irá:

1. ⏰ Executar a cada 5 minutos
2. 🔍 Buscar partidas ao vivo  
3. 🤖 Gerar análises com IA Gemini
4. 📱 Enviar apenas sinais de alta confiança
5. 🔄 Repetir automaticamente

**Sistema 100% automático rodando 24/7!** 🚀 