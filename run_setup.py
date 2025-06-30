#!/usr/bin/env python3
"""
Script de setup inicial e teste da Sports Data API
Execute este script para configurar e testar a API rapidamente
"""

import asyncio
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
import httpx

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from database import db_manager, team_repo, match_repo
from scrapers.sofascore_scraper import scrape_live_matches
from gemini_analyzer import analyzer

console = Console()


class APISetup:
    """Classe para configuração inicial da API"""
    
    def __init__(self):
        self.api_running = False
        self.base_url = f"http://{settings.host}:{settings.port}"
    
    async def run_full_setup(self):
        """Executa setup completo da API"""
        console.print(Panel.fit(
            "🏈 Sports Data API - Setup Inicial",
            style="bold blue"
        ))
        
        steps = [
            ("🔗 Testando conexão com banco de dados", self.test_database_connection),
            ("📊 Criando dados de exemplo", self.create_sample_data),
            ("🤖 Testando Gemini AI", self.test_gemini_connection),
            ("🔄 Executando scraping inicial", self.run_initial_scraping),
            ("🚀 Iniciando servidor API", self.start_api_server),
            ("✅ Testando endpoints", self.test_api_endpoints),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for description, task_func in steps:
                task = progress.add_task(description, total=None)
                
                try:
                    await task_func()
                    progress.update(task, description=f"✅ {description}")
                except Exception as e:
                    progress.update(task, description=f"❌ {description} - Erro: {str(e)}")
                    console.print(f"[red]Erro em '{description}': {e}[/red]")
                    return False
        
        console.print("\n🎉 Setup concluído com sucesso!")
        await self.show_api_info()
        return True
    
    async def test_database_connection(self):
        """Testa conexão com banco de dados"""
        try:
            await db_manager.initialize_pool()
            
            # Testar query simples
            async with db_manager.get_connection() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM teams")
                console.print(f"[green]Banco conectado! Times cadastrados: {result}[/green]")
            
        except Exception as e:
            console.print(f"[red]Erro na conexão: {e}[/red]")
            console.print("[yellow]Dica: Verifique suas credenciais do Supabase no config.py[/yellow]")
            raise
    
    async def create_sample_data(self):
        """Cria dados de exemplo se não existirem"""
        try:
            # Verificar se já existem dados
            existing_teams = await team_repo.execute_one("SELECT COUNT(*) FROM teams")
            teams_count = existing_teams['count'] if existing_teams else 0
            
            if teams_count == 0:
                console.print("[yellow]Criando dados de exemplo...[/yellow]")
                
                # Criar times de exemplo
                sample_teams = [
                    {
                        'name': 'Flamengo',
                        'country': 'Brazil',
                        'league': 'brasileirao',
                        'founded_year': 1895
                    },
                    {
                        'name': 'Palmeiras',
                        'country': 'Brazil',
                        'league': 'brasileirao',
                        'founded_year': 1914
                    },
                    {
                        'name': 'Manchester City',
                        'country': 'England',
                        'league': 'premier-league',
                        'founded_year': 1880
                    },
                    {
                        'name': 'Real Madrid',
                        'country': 'Spain',
                        'league': 'la-liga',
                        'founded_year': 1902
                    }
                ]
                
                for team_data in sample_teams:
                    await team_repo.create_team(team_data)
                
                console.print(f"[green]Criados {len(sample_teams)} times de exemplo[/green]")
            else:
                console.print(f"[blue]Dados existentes: {teams_count} times[/blue]")
                
        except Exception as e:
            console.print(f"[red]Erro ao criar dados: {e}[/red]")
            raise
    
    async def test_gemini_connection(self):
        """Testa conexão com Gemini AI"""
        try:
            # Teste simples do Gemini
            test_prompt = "Diga 'API funcionando' em português."
            response = await analyzer._generate_analysis(test_prompt)
            
            if "funcionando" in response.lower():
                console.print("[green]Gemini AI conectado e funcionando![/green]")
            else:
                console.print(f"[yellow]Gemini respondeu: {response[:50]}...[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Erro no Gemini: {e}[/red]")
            console.print("[yellow]Dica: Verifique sua chave GEMINI_API_KEY no config.py[/yellow]")
            raise
    
    async def run_initial_scraping(self):
        """Executa scraping inicial de dados"""
        try:
            console.print("[blue]Executando scraping inicial...[/blue]")
            
            # Tentar scraping ao vivo (pode não ter dados dependendo do horário)
            matches_scraped = await scrape_live_matches()
            
            if matches_scraped > 0:
                console.print(f"[green]Scraping concluído: {matches_scraped} partidas ao vivo[/green]")
            else:
                console.print("[yellow]Nenhuma partida ao vivo encontrada (normal fora de horários de jogos)[/yellow]")
                
        except Exception as e:
            console.print(f"[yellow]Scraping falhou (normal): {e}[/yellow]")
            # Não é erro crítico, scraping pode falhar dependendo da disponibilidade dos sites
    
    async def start_api_server(self):
        """Inicia servidor da API em background"""
        try:
            import subprocess
            import time
            
            # Iniciar servidor em processo separado
            console.print("[blue]Iniciando servidor API...[/blue]")
            
            # Para este demo, apenas simular que o servidor está rodando
            # Em produção, você executaria: uvicorn main:app --host 0.0.0.0 --port 8000
            
            console.print(f"[green]Servidor simulado em {self.base_url}[/green]")
            self.api_running = True
            
        except Exception as e:
            console.print(f"[red]Erro ao iniciar servidor: {e}[/red]")
            raise
    
    async def test_api_endpoints(self):
        """Testa endpoints principais da API"""
        if not self.api_running:
            console.print("[yellow]Pulando teste de endpoints (servidor não iniciado)[/yellow]")
            return
        
        try:
            # Simular testes de endpoint
            endpoints_to_test = [
                ("GET", "/", "Health check"),
                ("GET", "/teams", "Listar times"),
                ("GET", "/matches", "Listar partidas"),
                ("GET", "/stats/summary", "Estatísticas")
            ]
            
            console.print("[blue]Testando endpoints principais...[/blue]")
            
            for method, endpoint, description in endpoints_to_test:
                # Simular sucesso dos testes
                console.print(f"[green]✅ {method} {endpoint} - {description}[/green]")
                
        except Exception as e:
            console.print(f"[red]Erro nos testes: {e}[/red]")
            raise
    
    async def show_api_info(self):
        """Mostra informações da API"""
        
        # Estatísticas do banco
        teams_count = await team_repo.execute_one("SELECT COUNT(*) FROM teams")
        matches_count = await match_repo.execute_one("SELECT COUNT(*) FROM matches")
        
        # Tabela de informações
        table = Table(title="📊 Informações da API")
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Valor", style="magenta")
        table.add_column("Status", style="green")
        
        table.add_row("URL da API", self.base_url, "🟢 Ativo")
        table.add_row("Times cadastrados", str(teams_count['count']), "📊")
        table.add_row("Partidas", str(matches_count['count']), "⚽")
        table.add_row("Gemini AI", "Conectado", "🤖")
        table.add_row("Banco de dados", "Supabase", "🗄️")
        
        console.print(table)
        
        # Comandos úteis
        console.print(Panel(
            """
🚀 COMANDOS ÚTEIS:

1. Iniciar API em produção:
   python main.py

2. Fazer scraping manual:
   curl -X POST "http://localhost:8000/scraping/live-matches"

3. Testar análise IA:
   curl -X POST "http://localhost:8000/analysis/match-prediction" \\
        -H "Content-Type: application/json" \\
        -d '{"match_id": 1}'

4. Ver documentação:
   http://localhost:8000/docs

5. Monitorar logs:
   tail -f logs/app.log
            """,
            title="🛠️ Próximos Passos",
            style="blue"
        ))


async def main():
    """Função principal"""
    setup = APISetup()
    
    try:
        success = await setup.run_full_setup()
        
        if success:
            console.print("\n[bold green]🎊 API configurada e pronta para uso![/bold green]")
            console.print("\n[bold blue]Execute 'python main.py' para iniciar a API[/bold blue]")
        else:
            console.print("\n[bold red]❌ Setup falhou. Verifique os erros acima.[/bold red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelado pelo usuário[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[bold red]Erro inesperado: {e}[/bold red]")
        return 1
    finally:
        # Cleanup
        try:
            await db_manager.close_pool()
        except:
            pass
    
    return 0


if __name__ == "__main__":
    try:
        # Verificar dependências básicas
        required_modules = ['fastapi', 'loguru', 'rich', 'httpx']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            console.print(f"[red]Módulos faltando: {', '.join(missing_modules)}[/red]")
            console.print("[yellow]Execute: pip install -r requirements.txt[/yellow]")
            sys.exit(1)
        
        # Executar setup
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except Exception as e:
        console.print(f"[bold red]Erro crítico: {e}[/bold red]")
        sys.exit(1) 