import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np

POSITIONS = ['I', 'II', 'III', 'IV', 'V', 'VI']



def create_scores_series(points:pd.DataFrame, chosen_set:int)->pd.DataFrame:
    
    adversary_team_name = points.columns.drop(['lausanne', 'set'])[0]
    
    df = points.query(f'set == {chosen_set}').drop(columns='set').reset_index(drop=True)

    lausanne, bussigny = df['lausanne'], df[adversary_team_name]

    # Initialize the dataframe with the first point
    df = pd.DataFrame({'lausanne': [0.0], adversary_team_name: [0.0]})
    df = pd.DataFrame(columns=['lausanne', adversary_team_name])

    # Fill out the scores based on the serve-loss data
    lausanne_score = 0
    bussigny_score = 0
    point_number = 0

    # Process each point where lausanne loses serve
    for i in range(len(lausanne)):
        # Fill the points before lausanne loses the serve
        if not np.isnan(lausanne[i]):
            while lausanne_score < lausanne[i]:
                df.loc[point_number] = [lausanne_score, bussigny_score]
                lausanne_score += 1
                point_number += 1

        # Fill the points where bussigny loses the serve
        if not np.isnan(bussigny[i]):
            while bussigny_score < bussigny[i]:
                df.loc[point_number] = [lausanne_score, bussigny_score]
                bussigny_score += 1
                point_number += 1

    # Ensure the last point is added
    df.loc[point_number] = [lausanne_score, bussigny_score]

    df.index.name = 'total_points'
    df.reset_index(inplace=True)
    return df


def initialize_positions(df:pd.DataFrame, lineups:dict[int, pd.DataFrame], chosen_set:int)->pd.DataFrame:
    positions = ['I', 'II', 'III', 'IV', 'V', 'VI']
    for position in positions:
        df[position] = np.nan
    df.loc[0, positions] = lineups[chosen_set].loc['initial'].astype(int)
    df['new_server'] = df['lausanne'].diff().diff().fillna(0).replace({-1:0})
    return df


def rotate_positions(pos:list)->list:
    pos += [pos.pop(0)]
    return pos

def rotate_all_positions(df:pd.DataFrame)->pd.DataFrame:
    positions = ['I', 'II', 'III', 'IV', 'V', 'VI']

    positions_rotated = df.query('new_server == 1.0')[positions]
    pos = df.loc[0, positions].tolist()

    for idx, _ in positions_rotated.iterrows():
        pos = rotate_positions(pos)
        positions_rotated.loc[idx] = pos

    df.loc[df['new_server'] == 1.0, positions] = positions_rotated
    df = df.ffill()
    return df


def player_change_positions(df:pd.DataFrame, lineups:pd.DataFrame, chosen_set:pd.DataFrame)->pd.DataFrame:
    positions = ['I', 'II', 'III', 'IV', 'V', 'VI']

    changes = lineups[chosen_set].dropna(axis=1)
    if not changes.empty:
        for position, change in changes.T.iterrows():
            total_points = change['team_points'] + change['other_team_points']
            df.loc[df['total_points'] >= total_points, positions] = df.loc[df['total_points'] >= total_points, positions].replace({change['initial']:change['change']})
            
            if 'came_back_team_points' in change.index and change['came_back_team_points'] is not None:
                total_points = change['came_back_team_points'] + change['came_back_other_team_points']
                df.loc[df['total_points'] >= total_points, positions] = df.loc[df['total_points'] >= total_points, positions].replace({change['change']:change['initial']})
    return df



def switch_lib_in_V_VI_I(df:pd.DataFrame, players:pd.DataFrame)->pd.DataFrame:
    liberos = players.loc[players['position'] == 'L']
    if not liberos.empty:
        centrals = players.loc[players['position'] == 'C']
    lib_num = int(liberos['number'].values[0])
    centrals_num = centrals['number'].tolist()
    central_to_lib_dict = {
        central_num:lib_num for central_num in  centrals_num
    }
    df[['V', 'VI']] = df[['V', 'VI']].replace(central_to_lib_dict)
    
    df['point_won'] = df['lausanne'].diff().fillna(0)
    df.loc[df['point_won'] != 1, 'I'] = df.loc[df['point_won'] != 1, 'I'].replace(central_to_lib_dict)
    return df


def melt_set_data(df:pd.DataFrame, chosen_set:int, id_vars:list[str]=['total_points', 'I', 'II', 'III', 'IV', 'V', 'VI', 'new_server', 'point_won'], var_name:str='team', value_name:str='points')->pd.DataFrame:
    melted_df = pd.melt(df, id_vars=id_vars, var_name=var_name, value_name=value_name)
    melted_df['set'] = chosen_set
    return melted_df



def create_set_data(chosen_set:int, points:pd.DataFrame, lineups:dict[int, pd.DataFrame], players:pd.DataFrame)->pd.DataFrame:
    df = create_scores_series(points, chosen_set)
    df = initialize_positions(df, lineups, chosen_set)
    df = rotate_all_positions(df)
    df = player_change_positions(df, lineups, chosen_set)
    df = switch_lib_in_V_VI_I(df, players)
    melted_df = melt_set_data(df, chosen_set)
    return melted_df

def create_match_data(points:pd.DataFrame, lineups:dict[int, pd.DataFrame], players:pd.DataFrame)->pd.DataFrame:
    df = None
    for set_num in points['set'].unique():
        if df is None:
            df = create_set_data(set_num, points, lineups, players)
        else:
            df = pd.concat([df, create_set_data(set_num, points, lineups, players)], axis=0)
    return df


def create_positions_data(match_data:pd.DataFrame, numbers_to_position_dict:dict, numbers_to_players_dict:dict)->pd.DataFrame:
    positions_data = match_data.query("team == 'lausanne'").melt(var_name='position', value_name='number', id_vars=['total_points', 'new_server', 'point_won', 'points', 'set', 'team']).drop(columns='team')
    positions_data['role'] = positions_data['number'].map(numbers_to_position_dict)
    positions_data['name'] = positions_data['number'].map(numbers_to_players_dict)
    return positions_data
    
    
    
def create_plus_minus_data(positions_data:pd.DataFrame, numbers_to_position_dict:dict, players_to_number_dict:dict)->pd.DataFrame:
    plus_minus_data = pd.DataFrame(positions_data.query('total_points != 0')[['name', 'point_won']].value_counts()).reset_index('point_won')
    plus_minus_data = pd.merge(
        plus_minus_data.query('point_won == 0').drop(columns='point_won').rename(columns={'count':'points_lost'}),
        plus_minus_data.query('point_won == 1').drop(columns='point_won').rename(columns={'count':'points_won'}),
        left_index=True, right_index=True
    )
    plus_minus_data['plus_minus'] = (plus_minus_data['points_won'] - plus_minus_data['points_lost']) / (plus_minus_data['points_lost'] + plus_minus_data['points_won'])
    plus_minus_data = plus_minus_data.sort_values(by='plus_minus', ascending=False).reset_index()
    plus_minus_data['number'] = plus_minus_data['name'].map(players_to_number_dict)
    plus_minus_data['Position'] = plus_minus_data['number'].map(numbers_to_position_dict)
    return plus_minus_data



def create_serve_data(positions_data:pd.DataFrame, numbers_to_position_dict:dict, players_to_number_dict:dict)->pd.DataFrame:
    serve_data = positions_data.query("position == 'I' & point_won == 1")
    serve_data['new_server'] = serve_data['new_server'].cumsum()
    serve_data = serve_data.value_counts(subset=['new_server', 'name']).reset_index().drop(columns='new_server').groupby('name').mean().reset_index().sort_values(by="count", ascending=False)
    serve_data['position'] = serve_data['name'].apply(lambda name: numbers_to_position_dict[players_to_number_dict[name]])
    return serve_data