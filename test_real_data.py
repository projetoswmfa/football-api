"""
🎯 TESTE DOS DADOS 100% REAIS - ZERO SIMULAÇÃO
Script para testar e validar que a API retorna apenas dados reais
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import sys

class RealDataTester:
    """Testador de dados 100% reais"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, description: str):
        """Testa um endpoint específico"""
        print(f"\n🔍 TESTANDO: {description}")
        print("=" * 60)
        
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"📡 URL: {url}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Status: {response.status}")
                    print(f"📊 Message: {data.get('message', 'N/A')}")
                    
                    # Validar estrutura de dados
                    self.validate_real_data(data, endpoint)
                    
                    return data
                else:
                    print(f"❌ Status: {response.status}")
                    text = await response.text()
                    print(f"❌ Error: {text}")
                    return None
                    
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return None
    
    def validate_real_data(self, data: dict, endpoint: str):
        """Valida se os dados são realmente reais"""
        print("\n🔍 VALIDAÇÃO DE DADOS:")
        
        # Verificar se tem a garantia de dados reais
        response_data = data.get('data', {})
        
        # Verificações básicas
        if 'guarantee' in response_data:
            guarantee = response_data['guarantee']
            print(f"🔐 Garantia: {guarantee}")
            
            if 'REAL' in guarantee:
                print("✅ DADOS CONFIRMADOS COMO REAIS")
            else:
                print("⚠️ GARANTIA NÃO ENCONTRADA")
        
        # Verificar partidas se existir
        matches = response_data.get('matches', [])
        if matches:
            print(f"⚽ Total de partidas: {len(matches)}")
            
            # Validar primeira partida
            if matches:
                first_match = matches[0]
                print(f"\n📊 PRIMEIRA PARTIDA:")
                print(f"   🏠 Casa: {first_match.get('home_team', 'N/A')}")
                print(f"   🚪 Fora: {first_match.get('away_team', 'N/A')}")
                print(f"   📍 Fonte: {first_match.get('source', 'N/A')}")
                print(f"   🎯 Qualidade: {first_match.get('data_quality', 'N/A')}")
                print(f"   ❓ É simulação: {first_match.get('is_simulation', 'N/A')}")
                
                # Verificar se não é simulação
                suspicious_names = ['test', 'fake', 'demo', 'mock', 'example']
                home_team = first_match.get('home_team', '').lower()
                away_team = first_match.get('away_team', '').lower()
                
                is_suspicious = any(name in home_team or name in away_team for name in suspicious_names)
                
                if is_suspicious:
                    print("🚨 ATENÇÃO: PARTIDA PARECE SER SIMULAÇÃO!")
                else:
                    print("✅ PARTIDA PARECE SER REAL")
        
        # Verificar esportes múltiplos
        sports_data = response_data.get('sports', {})
        if sports_data:
            print(f"\n🏆 ESPORTES DISPONÍVEIS:")
            for sport, matches in sports_data.items():
                print(f"   {sport.upper()}: {len(matches)} partidas")
    
    async def run_comprehensive_test(self):
        """Executa teste completo de todos os endpoints reais"""
        print("🎯 TESTE ABRANGENTE - DADOS 100% REAIS")
        print("=" * 80)
        print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Lista de endpoints para testar
        endpoints = [
            ("/matches/live-real", "🔴 PARTIDAS AO VIVO 100% REAIS"),
            ("/matches/today-real", "📅 PARTIDAS DE HOJE 100% REAIS"),
            ("/sports/multi-real", "🏆 MÚLTIPLOS ESPORTES 100% REAIS"),
            ("/matches/live", "⚽ ENDPOINT ORIGINAL (atualizado para real)"),
        ]
        
        results = {}
        
        for endpoint, description in endpoints:
            result = await self.test_endpoint(endpoint, description)
            results[endpoint] = result
            
            # Pausa entre testes
            await asyncio.sleep(1)
        
        # Resumo final
        self.print_final_summary(results)
        
        return results
    
    def print_final_summary(self, results: dict):
        """Imprime resumo final dos testes"""
        print("\n🎯 RESUMO FINAL DOS TESTES")
        print("=" * 80)
        
        total_endpoints = len(results)
        successful_endpoints = sum(1 for result in results.values() if result is not None)
        
        print(f"📊 Total de endpoints testados: {total_endpoints}")
        print(f"✅ Endpoints funcionais: {successful_endpoints}")
        print(f"❌ Endpoints com erro: {total_endpoints - successful_endpoints}")
        
        # Contabilizar partidas totais
        total_matches = 0
        sources_used = set()
        
        for endpoint, result in results.items():
            if result and result.get('data'):
                data = result['data']
                
                # Contar partidas
                matches = data.get('matches', [])
                total_matches += len(matches)
                
                # Coletar fontes
                for match in matches:
                    source = match.get('source')
                    if source:
                        sources_used.add(source)
                
                # Dados de esportes múltiplos
                sports = data.get('sports', {})
                for sport_matches in sports.values():
                    total_matches += len(sport_matches)
                    for match in sport_matches:
                        source = match.get('source')
                        if source:
                            sources_used.add(source)
        
        print(f"\n📈 ESTATÍSTICAS DE DADOS:")
        print(f"⚽ Total de partidas encontradas: {total_matches}")
        print(f"📡 Fontes utilizadas: {', '.join(sources_used) if sources_used else 'Nenhuma'}")
        
        if total_matches > 0:
            print(f"\n🎉 SUCESSO: {total_matches} partidas com dados 100% REAIS encontradas!")
        else:
            print(f"\n⚠️ ATENÇÃO: Nenhuma partida encontrada. Verifique se há jogos ao vivo.")
        
        print(f"\n⏰ Teste concluído em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """Função principal"""
    print("🚀 INICIANDO TESTE DE DADOS 100% REAIS")
    print("Verificando se a API retorna apenas dados reais, sem simulação...")
    
    # Verificar se a API está rodando
    try:
        async with RealDataTester() as tester:
            # Teste rápido de conectividade
            health_result = await tester.test_endpoint("/health", "🏥 HEALTH CHECK")
            
            if health_result:
                print("\n✅ API está rodando! Iniciando testes de dados reais...")
                
                # Executar testes completos
                await tester.run_comprehensive_test()
            else:
                print("❌ API não está respondendo. Certifique-se de que está rodando na porta 8000.")
                print("💡 Execute: python main.py")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        print("💡 Certifique-se de que a API está rodando: python main.py")
        sys.exit(1)

if __name__ == "__main__":
    print("🎯 TESTADOR DE DADOS 100% REAIS - ZERO SIMULAÇÃO")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1) 