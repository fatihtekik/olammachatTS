import requests

r = requests.get('http://localhost:8000/api/v1/match-analysis/triggers-enhanced', params={'limit': 10})
print('Status:', r.status_code)

if r.status_code == 200:
    data = r.json()
    won2lost3 = [t for t in data if t['trigger_type'] == 'won_2_lost_3rd_set']
    
    if won2lost3:
        print(f'\n✅ Найдено {len(won2lost3)} триггеров won_2_lost_3rd_set')
        print(f'Evidence count: {len(won2lost3[0].get("evidence", []))}')
        if won2lost3[0].get('evidence'):
            ev = won2lost3[0]['evidence'][0]
            print(f'Sets count: {len(ev.get("sets", []))}')
            if ev.get('sets'):
                print(f'✅ Сеты есть: {ev["sets"][:3]}')
            else:
                print('❌ Сеты пустые')
    else:
        print('⚠️ Триггеров won_2_lost_3rd_set не найдено в первых 10')
