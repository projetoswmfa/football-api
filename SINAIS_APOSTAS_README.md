# 🚨 Sistema de Sinais de Apostas

Sistema automatizado que gera sinais inteligentes para **escanteios**, **cartões** e **ambas marcam** usando IA Gemini especialista em apostas esportivas.

## 🎯 O que faz

✅ Monitora partidas ao vivo automaticamente  
✅ Gera sinais com IA especialista (Gemini)  
✅ Sistema de confiança 1-10 (só envia ≥7)  
✅ Bot Telegram com comandos  
✅ Alertas premium para sinais ultra (≥8)  

## 🔧 Setup Rápido

### 1. Variáveis de Ambiente
```env
SPORTS_API_URL=http://localhost:8000
TELEGRAM_BOT_TOKEN=seu_bot_token
TELEGRAM_CHAT_ID=seu_chat_id
TELEGRAM_PREMIUM_CHAT_ID=chat_premium_opcional
```

### 2. Criar Bot Telegram
```bash
# Falar com @BotFather
/newbot
# Nome: SinaisApostasBot
# Username: @SeuSinaisBot
# Salvar o TOKEN gerado
```

### 3. Configurar Webhook
```bash
curl -X POST 'https://api.telegram.org/bot{TOKEN}/setWebhook' \
  -d 'url=https://seu-n8n.com/webhook/telegram-betting-commands'
```

## 🤖 Comandos Bot

| Comando | Descrição |
|---------|-----------|
| `/escanteios` | Sinal de escanteios |
| `/cartoes` | Sinal de cartões |
| `/ambas` | Sinal ambas marcam |
| `/todos` | Todos os sinais |
| `/help` | Lista comandos |

## 📊 Sistema de Confiança

- **1-6**: Não envia (baixa/média confiança)
- **7-8**: Envia normal (alta confiança)  
- **9-10**: Envia premium (ultra confiança)

## ⏰ Cronogramas

- **Sinais Automáticos**: A cada 5 minutos
- **Alertas Premium**: A cada 10 minutos  
- **Comandos Manuais**: Instantâneo

## 📁 Arquivos

- `SINAIS_APOSTAS_WORKFLOWS.json` - Workflows n8n
- `main.py` - API com endpoints de sinais
- Este README

## 🚀 Como Rodar

1. **Subir a API**: `python main.py`
2. **Importar workflows no n8n**
3. **Configurar variáveis de ambiente**
4. **Ativar os 3 workflows**
5. **Testar com `/help` no Telegram**

## 🎯 Endpoints API

```
POST /betting/corners-signal?match_id=123
POST /betting/cards-signal?match_id=123  
POST /betting/both-teams-score-signal?match_id=123
POST /betting/all-signals?match_id=123
```

## 🔥 Sistema Ultra Premium

Sinais com confiança ≥8/10 são enviados para chat premium separado, ideal para apostadores profissionais.

---

**🤖 Powered by Gemini AI Especialista em Apostas Esportivas** 