import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import time

ROLES = ["O", "A", "L", "C", "P"]
ROLES_PALETTE = 'Paired'
SET_PALETTE = 'tab10'
POINTS_PALETTE = 'viridis_r'

def plot_set_progress(melted_df:pd.DataFrame, chosen_set:int, lineups:dict[int, pd.DataFrame], timeouts:pd.DataFrame, numbers_to_players_dict:dict[int, str], ax):
    set_to_name = {i:f"{i}ème" for i in range(1,6)}
    set_to_name[1] = "1er"
    positions = ['I', 'II', 'III', 'IV', 'V', 'VI']


    ax = sns.lineplot(melted_df.query('set == @chosen_set'), x="total_points", hue="team", y="points", ax=ax)
    ax.set_xlabel("Total des points")
    ax.set_ylabel("Points par équipe")


    # starters = lineups[chosen_set].loc['initial'].astype(int).map(numbers_to_players_dict)
    starters = melted_df.query('set == @chosen_set').iloc[0][positions].map(numbers_to_players_dict)
    starters_string = ''
    for position in positions:
        starters_string += f"{position} {starters[position]}"
        if position != 'VI':
            starters_string += ', '
    starters_string = starters_string.strip()

    ax.set_title(f"{set_to_name[chosen_set]} Set: {starters_string}")
    ax.set_ylim(0, melted_df.query('set == @chosen_set')['points'].max())
    ax.set_xlim(0, melted_df.query('set == @chosen_set')['total_points'].max())


    set_timeouts = timeouts.query('set == @chosen_set')
    if not set_timeouts.empty:
        for _, timeout in set_timeouts.iterrows():
            total_points = timeout['team_points'] + timeout['other_team_points']
            ax.axvline(total_points, label=f"Temp mort ({total_points}): {timeout['team']}", color='r', linestyle='--', alpha=0.5)

    changes = lineups[chosen_set].dropna(axis=1)
    if not changes.empty:
        for position, change in changes.T.iterrows():
            total_points = change['team_points'] + change['other_team_points']
            idx_pos_changed = melted_df.query("(set == @chosen_set) & (team == 'lausanne') & (total_points == @total_points)")[positions].values.squeeze().tolist().index(change['change'])
            
            ax.axvline(total_points, label=f"Changement ({total_points}): {positions[idx_pos_changed]} {numbers_to_players_dict[change['initial']]} <> {numbers_to_players_dict[change['change']]}", color='b', linestyle=':', alpha=0.5)
            
            
            if 'came_back_team_points' in change.index and change['came_back_team_points'] is not None:
                total_points = change['came_back_team_points'] + change['came_back_other_team_points']
                idx_pos_changed = melted_df.query("(set == @chosen_set) & (team == 'lausanne') & (total_points == @total_points)")[positions].values.squeeze().tolist().index(change['initial'])
                ax.axvline(total_points, label=f"Changement ({total_points}): {positions[idx_pos_changed]} {numbers_to_players_dict[change['change']]} <> {numbers_to_players_dict[change['initial']]}", color='b', linestyle=':', alpha=0.5)
    ax.legend()
    ax.grid()
    # sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    return ax



def plot_points_at_each_position(ax, positions_data:pd.DataFrame):
    sns.countplot(positions_data.query('total_points - points  != 25'), hue='position', x='name', order=positions_data['name'].value_counts().index, stat='count', ax=ax)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
    ax.set_ylabel("Points joués")
    ax.set_xlabel("Joueurs")
    ax.grid(axis='y', which='both')
    ax.set_title("Points Joués par Position")
    return ax



def plot_points_played(ax, positions_data:pd.DataFrame):
    sns.countplot(positions_data.query('total_points - points  != 25'), hue='role', x='name', order=positions_data['name'].value_counts().index, ax=ax, hue_order=ROLES, palette=ROLES_PALETTE)
    ax.set_ylabel("Points joués")
    ax.set_xlabel("Joueurs")
    for label in ax.containers:
        ax.bar_label(label)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
    ax.set_title("Points Joués par Joueurs")
    return ax


def plot_plus_minus(ax, plus_minus_data:pd.DataFrame):
    sns.barplot(plus_minus_data, y='plus_minus', x='name', hue='Position', ax=ax, hue_order=ROLES, palette=ROLES_PALETTE)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
    return ax


def plot_points_won_and_lost(ax, positions_data:pd.DataFrame):
    sns.countplot(positions_data.query('(total_points != 0)').replace({1.0: "Gagné", 0.0:"Perdu"}), hue='point_won', x='name', order=positions_data['name'].value_counts().index, palette='viridis_r', ax=ax)
    for label in ax.containers:
        ax.bar_label(label)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
    ax.legend(title = "Point")
    return ax


def plot_serve_switches(ax, positions_data:pd.DataFrame):
    sns.histplot(positions_data.query("new_server == 1 & position == 'I'"), hue='set', x='name', multiple='stack', ax=ax)
    # ax.grid(axis='y', which='both')
    # for label in ax.containers:
    #     ax.bar_label(label)
    ax.set_ylabel("Nombre de Passages au Service")
    ax.set_xlabel("Joueurs")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
    ax.set_title("Nombre de Passages au Service")
    return ax


def plot_serve_instances(ax, positions_data:pd.DataFrame):
    # for set in [5, 4, 3, 2, 1]:
    #     sns.countplot(positions_data.query(f"position == 'I' & point_won == 1 & set <= {set}"), x='name', ax=ax)
    sns.histplot(positions_data.query("position == 'I' & point_won == 1"), hue='set', x='name', multiple='stack', ax=ax, palette='tab10', hue_order=list(range(positions_data['set'].max(), 0, -1)))
    # ax.grid(axis='y', which='both')
    # for label in ax.containers:
    #     ax.bar_label(label)
    ax.set_ylabel("Nombre de Service fais")
    ax.set_xlabel("Joueurs")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=80)
    ax.set_title("Nombre de Service fais")
    return ax


def plot_serve_percentage(ax, serve_data:pd.DataFrame):
    sns.barplot(serve_data, x="name", y="count", hue="position", hue_order=ROLES, ax=ax, palette=ROLES_PALETTE)
    for label in ax.containers:
        ax.bar_label(
            label,
            fmt="{:.3}"
        )
    return ax
    
    
    
def plot_set_durations_from_time(ax, results:pd.DataFrame):
    results['duration_in_mins'] = results['duration'].map(lambda d : time.fromisoformat(str(d)).minute)
    sns.barplot(results, x='set', y='duration_in_mins', hue='set', legend=None, ax=ax, palette='viridis')
    ax.grid(axis='y')
    ax.set_ylabel("Durée (min)")
    ax.set_title("Durée de chaque Set")
    return ax

def plot_set_durations(ax, durations:pd.DataFrame):
    sns.barplot(durations, x='set', y='duration', hue='set', legend=None, ax=ax, hue_order=list(range(durations['set'].max(), 0, -1)), palette='tab10')
    # ax.grid(axis='y')
    ax.set_ylabel("Durée (min)")
    ax.set_title("Durée de chaque Set")
    for label in ax.containers:
        ax.bar_label(label)
    return ax
