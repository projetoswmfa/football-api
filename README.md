# 🏈 Sports Data API

Uma API completa para scraping e análise de dados esportivos com inteligência artificial usando Gemini.

## 🚀 Funcionalidades

### ✅ Scrapers Implementados
- **Sofascore**: Partidas ao vivo, placares, estatísticas em tempo real
- **Transfermarkt**: Elencos, jogadores, valores de mercado
- **Sistema de Rate Limiting**: Proteção contra bloqueios

### 🤖 Análises com IA (Gemini)
- **Previsões de Partidas**: Análise preditiva baseada em dados históricos
- **Tendências de Apostas**: Identificação de oportunidades de valor
- **Forma dos Times**: Análise da performance recente
- **Performance de Jogadores**: Avaliação individual detalhada

### 📊 Banco de Dados (Supabase)
- **Times**: Informações completas, logos, estatísticas
- **Jogadores**: Posições, idades, valores de mercado
- **Partidas**: Dados completos incluindo ao vivo
- **Análises**: Histórico de todas as análises da IA

### ⚡ Recursos Avançados
- **Agendamento Automático**: Scrapers executam automaticamente
- **Rate Limiting Inteligente**: Evita bloqueios de IP
- **Cache e Performance**: Otimizado para alta velocidade
- **Monitoramento**: Logs detalhados e métricas

## 🛠️ Tecnologias

- **Backend**: FastAPI + Python 3.11+
- **Banco de Dados**: Supabase (PostgreSQL)
- **IA**: Google Gemini Pro
- **Scraping**: ScraperFC, Playwright, BeautifulSoup
- **Agendamento**: APScheduler
- **Logging**: Loguru

## 📋 Pré-requisitos

- Python 3.11+
- Conta Supabase
- Chave da API do Google Gemini
- Redis (opcional, para cache)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd sports-data-api
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
Crie um arquivo `.env` baseado no `config.py`:

```env
# Database - Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-supabase-anon
DATABASE_URL=postgresql://postgres:senha@db.supabase.co:5432/postgres

# Google Gemini AI  
GEMINI_API_KEY=AIzaSyBpFb-rdZIVGIs-oZQ7VJlEnbPJGeTNnzI

# Configurações da API
DEBUG=True
PORT=8000
LOG_LEVEL=INFO

# Rate Limiting
REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_REQUESTS=10

# Scrapers
ENABLE_LIVE_SCRAPING=True
ENABLE_TEAM_SCRAPING=True
ENABLE_PLAYER_SCRAPING=True

# Ligas para scraping
LEAGUES=brasileirao,champions-league,premier-league,la-liga
```

### 4. Configure o banco de dados
Execute o schema SQL no seu projeto Supabase:

```bash
# No dashboard do Supabase, execute o conteúdo de schema.sql
```

### 5. Instale o Playwright (para scraping avançado)
```bash
playwright install
```

## 🚀 Executando a API

### Desenvolvimento
```bash
python main.py
```

### Produção
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

A API estará disponível em: `http://localhost:8000`

## 📖 Documentação da API

### Endpoints Principais

#### 🏠 Health Check
```
GET /              # Status básico
GET /health        # Health check detalhado
```

#### 🏆 Times
```
GET /teams                    # Lista times com paginação
GET /teams/{team_id}          # Busca time específico  
POST /teams                   # Cria novo time
GET /teams/{team_id}/players  # Jogadores do time
```

#### 👤 Jogadores
```
GET /players/{player_id}      # Busca jogador específico
POST /players                 # Cria novo jogador
```

#### ⚽ Partidas
```
GET /matches                  # Lista partidas com filtros
GET /matches/live             # Partidas ao vivo
GET /matches/{match_id}       # Busca partida específica
POST /matches                 # Cria nova partida
```

#### 🔄 Scraping
```
POST /scraping/live-matches         # Dispara scraping ao vivo
POST /scraping/teams/{league}       # Scraping de times por liga
```

#### 🤖 Análises IA
```
POST /analysis/match-prediction     # Previsão de partida
POST /analysis/betting-trends       # Tendências de apostas
POST /analysis/team-form           # Forma do time
GET /analysis/{analysis_id}        # Busca análise específica
```

#### 📊 Estatísticas
```
GET /stats/summary            # Resumo geral da API
```

### Exemplos de Uso

#### Previsão de Partida
```bash
curl -X POST "http://localhost:8000/analysis/match-prediction" \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": 1,
    "include_team_form": true,
    "include_head_to_head": true,
    "analysis_depth": "detailed"
  }'
```

#### Scraping de Times
```bash
curl -X POST "http://localhost:8000/scraping/teams/brasileirao?max_teams=5"
```

#### Buscar Partidas Ao Vivo
```bash
curl "http://localhost:8000/matches/live"
```

## 🔐 Configuração do Supabase

### 1. Crie um novo projeto no Supabase

### 2. Execute o schema SQL
Use o conteúdo do arquivo `schema.sql` no SQL Editor do Supabase.

### 3. Configure RLS (Row Level Security)
```sql
-- Exemplo de política RLS para times
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Teams são públicos" ON teams
    FOR SELECT USING (true);
```

### 4. Obtenha as credenciais
- **URL**: Na seção Settings > API
- **Chave Anon**: Na seção Settings > API

## 🤖 Configuração do Gemini

### 1. Obtenha uma chave da API
- Acesse: https://makersuite.google.com/app/apikey
- Crie uma nova chave API

### 2. Configure a chave no ambiente
```env
GEMINI_API_KEY=sua-chave-aqui
```

## 📊 Monitoramento e Logs

### Logs da Aplicação
```bash
# Logs em tempo real
tail -f logs/app.log

# Filtrar por nível
grep "ERROR" logs/app.log
```

### Status do Scheduler
```bash
curl "http://localhost:8000/stats/summary"
```

## 🔧 Configurações Avançadas

### Rate Limiting
Configure no `.env`:
```env
REQUESTS_PER_MINUTE=60        # Requests por minuto
MAX_CONCURRENT_REQUESTS=10    # Requests simultâneos
```

### Intervalos de Scraping
```env
LIVE_MATCHES_INTERVAL=60      # 60 segundos para ao vivo
TEAM_STATS_INTERVAL=86400     # 24 horas para times
PLAYER_STATS_INTERVAL=43200   # 12 horas para jogadores
```

## 🚨 Troubleshooting

### Erro de Conexão com Supabase
```bash
# Teste a conexão
python -c "
import asyncio
from database import db_manager
async def test():
    await db_manager.initialize_pool()
    print('Conexão OK')
asyncio.run(test())
"
```

### Erro no Gemini
```bash
# Teste a API do Gemini
python -c "
import google.generativeai as genai
genai.configure(api_key='sua-chave')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print(response.text)
"
```

### Rate Limiting do Transfermarkt
- Reduza `max_teams` nos endpoints de scraping
- Aumente os delays no código
- Use proxies rotativos se necessário

## 📈 Performance

### Otimizações Implementadas
- **Pool de Conexões**: AsyncPG com pool otimizado
- **Índices de Banco**: Índices estratégicos para queries frequentes
- **Rate Limiting**: Evita bloqueios e overload
- **Async/Await**: Processamento não-bloqueante
- **Paginação**: Responses otimizadas

### Métricas Esperadas
- **Throughput**: ~1000 requests/min
- **Latência**: <100ms para queries simples
- **Scraping**: ~50 partidas ao vivo/min

## 🔮 Roadmap

### Próximas Funcionalidades
- [ ] WebSocket para dados em tempo real
- [ ] Cache Redis para performance
- [ ] Dashboard web interativo
- [ ] Notificações push para eventos importantes
- [ ] Integração com mais sites de dados esportivos
- [ ] API de predições avançadas
- [ ] Sistema de alertas personalizados

### Melhorias Planejadas
- [ ] Testes automatizados completos
- [ ] Deploy com Docker
- [ ] CI/CD com GitHub Actions
- [ ] Documentação interativa
- [ ] Métricas e monitoramento avançado

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 🆘 Suporte

- **Issues**: Use o sistema de issues do GitHub
- **Documentação**: Consulte este README e os comentários no código
- **Performance**: Monitore os logs para identificar gargalos

## 🎯 Casos de Uso

### Para Apostadores
- Análises preditivas baseadas em dados reais
- Identificação de apostas com valor
- Monitoramento de odds em tempo real

### Para Analistas Esportivos
- Dados históricos abrangentes
- Comparações estatísticas avançadas
- Insights gerados por IA

### Para Desenvolvedores
- API RESTful completa e documentada
- Exemplos de scraping ético e eficiente
- Integração com IA para análises

---

💡 **Dica**: Para começar rapidamente, execute primeiro o scraping de algumas ligas principais e depois teste as análises de IA!

🚀 **Performance**: A API é otimizada para processar milhares de partidas e análises simultaneamente.

🔒 **Segurança**: Rate limiting e validação rigorosa protegem contra abusos.

📱 **Escalabilidade**: Arquitetura assíncrona permite fácil escalabilidade horizontal. 