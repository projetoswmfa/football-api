"""
Teste Completo do Sistema de Placares em Tempo Real
"""
import asyncio
import requests
import json
from datetime import datetime

def test_api_endpoints():
    """Testar todos os endpoints da API relacionados a placares"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 TESTE COMPLETO DO SISTEMA DE PLACARES EM TEMPO REAL")
    print("=" * 60)
    
    # 1. Verificar se API está funcionando
    print("\n1️⃣ Testando conectividade da API...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print(f"✅ API Status: {response.status_code}")
            data = response.json()
            print(f"📄 Versão: {data.get('version')}")
            print(f"🗄️ Database: {data.get('database')}")
        else:
            print(f"❌ API retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar API: {e}")
        return False
    
    # 2. Testar endpoint de atualização de placares
    print("\n2️⃣ Testando atualização de placares em tempo real...")
    try:
        response = requests.post(f"{base_url}/live-scores/update")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Atualização: {data.get('success')}")
            print(f"📊 Partidas encontradas: {data.get('matches_found', 0)}")
            print(f"🔄 Partidas atualizadas: {data.get('matches_updated', 0)}")
            print(f"🌐 Fontes: {data.get('sources', [])}")
            
            # Mostrar algumas partidas
            matches = data.get('data', [])
            if matches:
                print(f"\n📋 Primeiras 3 partidas encontradas:")
                for i, match in enumerate(matches[:3]):
                    print(f"   {i+1}. {match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}")
                    print(f"      ⏱️ {match.get('minute', 0)}' | 🏆 {match['competition']} | 📡 {match['source']}")
        else:
            print(f"❌ Erro na atualização: {response.status_code}")
            print(f"📄 Resposta: {response.text}")
    except Exception as e:
        print(f"❌ Erro no teste de atualização: {e}")
    
    # 3. Testar endpoint de placares atuais
    print("\n3️⃣ Testando busca de placares atuais...")
    try:
        response = requests.get(f"{base_url}/live-scores/current")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Busca: {data.get('success')}")
            print(f"📊 Partidas ao vivo no banco: {data.get('matches_found', 0)}")
            
            matches = data.get('data', [])
            if matches:
                print(f"\n🔴 PLACARES AO VIVO NO BANCO:")
                for match in matches:
                    print(f"   📊 {match['home_team_name']} {match['current_score_home']}-{match['current_score_away']} {match['away_team_name']}")
                    print(f"      ⏱️ {match['current_minute']}' | 🏆 {match['competition']}")
                    print(f"      🏟️ {match.get('venue', 'N/A')} | 📡 {match['source']}")
                    print(f"      🕐 Última atualização: {match['last_updated']}")
                    print()
            else:
                print("ℹ️ Nenhuma partida ao vivo encontrada no banco")
        else:
            print(f"❌ Erro na busca: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no teste de busca: {e}")
    
    # 4. Testar endpoint antigo para comparação
    print("\n4️⃣ Testando endpoint antigo (/matches/live)...")
    try:
        response = requests.get(f"{base_url}/matches/live")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint antigo: {data.get('success')}")
            print(f"📊 Dados antigos: {data.get('count', 0)} registros")
        else:
            print(f"❌ Endpoint antigo falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no endpoint antigo: {e}")
    
    # 5. Buscar partida específica (Inter Milan x Fluminense)
    print("\n5️⃣ Buscando partida específica: Inter Milan x Fluminense...")
    try:
        response = requests.get(f"{base_url}/live-scores/current")
        if response.status_code == 200:
            data = response.json()
            matches = data.get('data', [])
            
            inter_fluminense = None
            for match in matches:
                home = match['home_team_name'].lower()
                away = match['away_team_name'].lower()
                
                if (('inter' in home and 'fluminense' in away) or 
                    ('fluminense' in home and 'inter' in away) or
                    ('milan' in home and 'fluminense' in away) or
                    ('fluminense' in home and 'milan' in away)):
                    inter_fluminense = match
                    break
            
            if inter_fluminense:
                print("🎯 JOGO ENCONTRADO!")
                print(f"⚽ {inter_fluminense['home_team_name']} {inter_fluminense['current_score_home']}-{inter_fluminense['current_score_away']} {inter_fluminense['away_team_name']}")
                print(f"⏱️ {inter_fluminense['current_minute']}' | Status: {inter_fluminense['status']}")
                print(f"🏆 {inter_fluminense['competition']}")
                print(f"🏟️ {inter_fluminense.get('venue', 'N/A')}")
                print(f"📡 Fonte: {inter_fluminense['source']}")
                print(f"🕐 Última atualização: {inter_fluminense['last_updated']}")
            else:
                print("❌ Inter Milan x Fluminense não encontrado nos dados atuais")
                
    except Exception as e:
        print(f"❌ Erro na busca específica: {e}")
    
    print("\n" + "=" * 60)
    print("✅ TESTE COMPLETO FINALIZADO!")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

def print_usage_instructions():
    """Mostrar instruções de uso"""
    print("\n📖 INSTRUÇÕES DE USO:")
    print("=" * 40)
    print("1. Para atualizar placares: POST /live-scores/update")
    print("2. Para ver placares atuais: GET /live-scores/current")
    print("3. Para buscar um jogo específico: filtrar nos dados de /live-scores/current")
    print("4. Para executar scheduler automático: python live_scores_scheduler.py")
    print("\n🌐 Fontes de dados integradas:")
    print("   - SofaScore (placares europeus)")
    print("   - ESPN (placares internacionais)")
    print("   - Dados atualizados a cada 30 segundos")

if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print_usage_instructions() 