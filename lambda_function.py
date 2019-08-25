import json

from requests_html import HTMLSession
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
import pandas as pd

def parse_odds(odds):
    if (type(odds)==str) and (len(odds) > 0):
        if '/' in odds:
            a, b = odds.split('/')
            a = int(a)
            b = int(b)
        else:
            a = int(odds)
            b = 1
        return b / (a + b)
    return np.nan



def lambda_handler(event, context):
    url = f'https://www.oddschecker.com/football/english/premier-league'
    bankroll = 100
    
    session = HTMLSession()
    request = session.get(url)
    
    soup = BeautifulSoup(request.text, 'html.parser')
    table = soup.find('div', {'id':'fixtures'})
    rows = table.findAll('tr')
    
    processed_rows = []
    for row in rows:
        if 'hda-header' in row['class']:
            date = parser.parse(row.find('td').text)
        else:
            try:
                home, draw, away = [parse_odds(x.text) for x in row.findAll('p', {'class':'participant-name'})]
            except ValueError: 
                pass
            
            finally:
                team_names = []
                for raw_team_name in row.findAll('p', {'class':'fixtures-bet-name beta-footnote'}):
                    if raw_team_name.find('span') is None:
                        team_name = raw_team_name.text
                    else:
                        team_name = raw_team_name.text[:-5]
                    team_names.append(team_name)
    
                home_team, away_team  = team_names
                prow = pd.Series([date, home_team, away_team, home, draw, away], 
                                 index=['Date', 'Home Team', 'Away Team', 'Home', 'Draw', 'Away'])
                processed_rows.append(prow)
    
    stats = pd.DataFrame(processed_rows)    
    stats.to_csv(f'game_odds_{datetime.today().strftime("%Y%m%dT%H%M%S")}.csv')
    
    stats.set_index(['Date', 'Home Team', 'Away Team'], inplace=True)
    
    norm_stats = stats.div(stats.sum(axis=1), axis=0)
    
    bet_amounts = norm_stats.mul(1-stats.sum(axis=1), axis=0)
    bet_amounts = bet_amounts[bet_amounts > 0]
    bet_amounts = bet_amounts.mul(bankroll / bet_amounts.sum(axis=1), axis=0)
    bet_amounts.dropna(inplace=True)
    
    b = pd.concat([bet_amounts, bet_amounts.sum(axis=1).rename('Total')], axis=1).applymap(lambda x: f'£{x:0.2f}')
    c = bet_amounts.div(stats, axis=0).dropna().applymap(lambda x: f'£{x:0.2f}')
    d = bet_amounts.div(stats, axis=0).sub(bet_amounts.sum(axis=1), axis=0).dropna().applymap(lambda x: f'£{x:0.2f}')
    
    return {
        'statusCode': 200,
        'body': json.dumps([b, c, d])
    }
