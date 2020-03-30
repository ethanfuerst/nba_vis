import pandas as pd
pd.options.display.max_columns = None
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
import datetime
import html5lib
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo, playergamelog, playercareerstats, shotchartdetail

# Custom errors
class PlayerNotFoundError(Exception):
    pass

class SeasonNotFoundError(Exception):
    pass

class NBA_Player:
    def __init__(self, player_name, print_name=True):
        '''
        Player object from nba_api

        Parameters:

        player_name (string, required)
            The name of the player. If name is too general, then first name in the search will be returned.
                Ex. 'luka doncic' or 'harden'
            If the search does not return a player, a PlayerNotFoundError will be thrown.

        print_name (boolean, default: True)
            Will print the name of the player on default to make sure that you're querying the player that you want.
            If you don't want this done, you can pass it False
        '''

        # Search for the player to get the id
        player_search = players.find_players_by_full_name(player_name)

        # If no results for the player, throw an error
        if len(player_search) == 0:
            raise PlayerNotFoundError('Name not found in database. Try being more specific or look for the player here: https://stats.nba.com/players/')

        # Get the id from the result of my search
        self.player_id = player_search[0]['id']
        self.name = player_search[0]['full_name']
        self.first_name = player_search[0]['first_name']
        self.last_name = player_search[0]['last_name']
        self.is_active = player_search[0]['is_active']
        # Create a df that outlines the players career
        df = self.get_career()
        df = df[df['Team'] != 'TOT'][['Season', 'Team', 'TEAM_ID']].copy()
        df['start'] = df['Season'].apply(lambda x: int(x[:4]))
        df['end'] = df['start'] + 1
        self._career = df.rename({'TEAM_ID': 'Team ID', 'start': 'season'}, axis=1)[['Team ID', 'season']]
        cond = df.end.sub(df.end.shift()).ne(1) | (df.Team.ne(df.Team.shift()))
        no_year_end_change = df.end.shift(-1).sub(df.end).eq(0)
        df['change'] = df.loc[cond,'start']
        df['end_edit'] = np.where(no_year_end_change,df.start,df.end)
        df['change'] = df.change.ffill().astype('Int64')
        df = df.groupby(['Team','TEAM_ID','change']).end_edit.max().reset_index()
        df['Years'] = df.change.astype(str).str.cat(df.end_edit.astype(str),sep='-')
        df = df.sort_values(['change', 'end_edit'])
        df = df.drop(['change','end_edit'],axis = 1)
        df = df.rename({'TEAM_ID': 'Team ID'}, axis='columns')
        self.career = df

        if print_name:
            print(self.name)
    
    def get_season(self, season=datetime.datetime.today().year - 1, season_type='regular'):
        '''
        Returns a df of player game logs from the 'season to season+1' season.
        Specify 'regular', 'preseason', 'playoffs' or 'allstar'.

        Parameters:

        season (int, default: current year - 1)
            The season that you want to pull data from. 
                Ex. 2003
            If the player you specified doesn't have date from the season inputted, a SeasonNotFoundError will be thrown.
            
        season_type (string, default: 'regular')
            The period of games from which you'd like the data from.
            Must be one of the following:
                'regular' - Regular Season
                'preseason' - Pre-Season
                'playoffs' - Playoffs
                'allstar' - All-Star
            If season_type is not one of the values above, it will be changed to 'regular'.

        Returns:

        df
            A pd.DataFrame() containing the player data with the following columns:
                ['Season', 'Player', 'Game_ID', 'GAME_DATE', 'MATCHUP', 'WL',
                'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
                'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF',
                'PTS', 'PLUS_MINUS']
        '''
        # Change season_type to 'regular' if not specified correctly
        if season_type not in ['regular', 'preseason', 'playoffs', 'allstar']:
            season_type = 'regular'
        
        s_types = {'regular':'Regular Season', 'preseason':'Pre-Season', 'playoffs':'Playoffs', 'allstar':'All-Star'}
        s_type = s_types[season_type]

        # playergamelog is a nba_api endpoint that contains the dataframes
        try:
            log = playergamelog.PlayerGameLog(player_id=self.player_id, season=season, season_type_all_star=s_type)
        except:
            return pd.DataFrame()

        # If no results for the season, throw an error
        if len(log.get_data_frames()[0]) == 0:
            raise SeasonNotFoundError(self.name + " doesn't have data recorded for the " +  str(season) + " season." )

        df = log.get_data_frames()[0]
        df['Player'] = self.name
        df['Season'] = str(season) + "-" + str(season + 1)[2:]
        df['TS_PCT'] = round(df['PTS'] / (2*(df['FGA'] + (.44 * df['FTA']))),3)

        # Drop the 'video available' column and reorder
        df = df[['Season', 'Player', 'Game_ID', 'GAME_DATE', 'MATCHUP', 'WL',
                'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
                'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF',
                'PTS', 'PLUS_MINUS']]
        
        return df

    def get_career(self):
        '''
        Returns a df of the player's totals and percentages for all season in the player's career.

        Parameters:

        season (int, default: current year - 1)
            The season that you want to pull data from. 
                Ex. 2003
            If the player you specified doesn't have date from the season inputted, a SeasonNotFoundError will be thrown.
        
        Returns:

        df
            A pd.DataFrame() containing the player data with the following columns:
                ['Player', 'Season', 'Team', 'TEAM_ID', 
                'PLAYER_AGE', 'GP', 'GS', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A',
                'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 
                'STL', 'BLK', 'TOV', 'PF', 'PTS']
        '''
        # see more on https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/playercareerstats.md
        log = playercareerstats.PlayerCareerStats(player_id=self.player_id, per_mode36='Totals')
        df = log.get_data_frames()[0]

        df['Player'] = self.name
        df['Season'] = df['SEASON_ID'].copy()
        df['Team'] = df['TEAM_ABBREVIATION'].copy()
        df['TS_PCT'] = round(df['PTS'] / (2*(df['FGA'] + (.44 * df['FTA']))),3)

        # Specify column order
        df = df[['Player', 'Season', 'Team', 'TEAM_ID', 
                'PLAYER_AGE', 'GP', 'GS', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A',
                'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 
                'STL', 'BLK', 'TOV', 'PF', 'PTS']].copy()
                
        return df

    def get_full_career(self, season_type='regular'):
        '''
        Returns a df of the player's game logs for all season in the player's career.

        Parameters:

        season_type (string, default: 'regular')
            The period of games from which you'd like the data from.
            Must be one of the following:
                'regular' - Regular Season
                'preseason' - Pre-Season
                'playoffs' - Playoffs
                'allstar' - All-Star
                'full' - Regular Season and Playoffs
                'all' - Pre-Season, Regular Season, Playoffs and All-Star
                'no_all_star' - Pre-Season, Regular Season and Playoffs
            If season_type is not one of the values above, it will be changed to 'regular'.
        
        Returns:

        df
            A pd.DataFrame() containing the player data with the following columns:
                ['Player', 'Season', 'Team', 'TEAM_ID', 
                'PLAYER_AGE', 'GP', 'GS', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A',
                'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 
                'STL', 'BLK', 'TOV', 'PF', 'PTS']
        '''
        # Get list of seasons with data
        career_seasons = self.get_career()
        seasons = [int(i[:4]) for i in career_seasons['Season'].values.astype(str)]

        # Get data from each season
        df = pd.DataFrame()
        for i in seasons:
            if season_type == 'preseason' or season_type == 'all' or season_type == 'no_all_star':
                try:
                    df_1 = self.get_season(i, season_type='preseason')
                    df_1['Season Type'] = 'PRE'
                    df = df.append(df_1)
                except SeasonNotFoundError:
                    pass
            if season_type == 'regular' or season_type == 'full' or season_type == 'all' or season_type == 'no_all_star':
                try:
                    df_2 = self.get_season(i, season_type='regular')
                    df_2['Season Type'] = 'REG'
                    df = df.append(df_2)
                except SeasonNotFoundError:
                    pass
            if season_type == 'playoffs' or season_type == 'full' or season_type == 'all' or season_type == 'no_all_star':
                # Add flag if player had no data in playoffs
                try:
                    df_3 = self.get_season(i, season_type='playoffs')
                    df_3['Season Type'] = 'PLAY'
                    df = df.append(df_3)
                except SeasonNotFoundError:
                    pass
            if season_type == 'allstar' or season_type == 'all':
                try:
                    df_4 = self.get_season(i, season_type='allstar')
                    df_4['Season Type'] = 'ALLSTAR'
                    df = df.append(df_4)
                except SeasonNotFoundError:
                    pass

        df.reset_index(inplace=True)
        df = df[['Season', 'Season Type', 'Player', 'Game_ID', 'GAME_DATE', 'MATCHUP', 'WL', 
                'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
                'FT_PCT', 'TS_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV',
                'PF', 'PTS', 'PLUS_MINUS']].copy()
        cols_as_int = ['MIN', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 
                        'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLUS_MINUS']
        df[cols_as_int] = df[cols_as_int].astype(int)

        return df
    
    def get_shot_chart(self, seasons=None):
        '''
        Returns a matplotlib fig of the player's shot chart given certain parameters.

        Parameters:

        seasons (list of integers, default: None)
            The seasons (inclusive) for which you'd like to get data from.
            Must be a list of length 1 or two containing integers of the seasons.
            Example: [2005, 2018]
            If season_type is not one of the values above, it will be changed to 'regular'.
        
        Returns:

        fig
            Matplotlib figure of shotchart
        '''
        # Start with just seasons then do teams and seasons
        # If given a list fo season start and end, create a list of all team ids and seasons
        # Default season is the first season of the first team
        # if team_id is None:
        #     team_id = self.career['Team ID'].iloc[0]
        if seasons is None:
            f_seas = int(self.career['Years'].iloc[0][:4])
            seasons = [f_seas]
        if len(seasons) > 2 or type(seasons) != list or type(seasons[0]) != int:
            raise TypeError('The seasons variable must be a list of length 2 or 1 with years in integer form. Example: [2005, 2018]')
        else:
            # Get the seasons from ref between two dates
            first = seasons[0]
            if len(seasons) == 1:
                last = seasons[0]
            else:
                last = seasons[1]
            # Get all seasons and team ID between first and last
            season_df = self._career[(self._career['season'].astype(int) >= first) & (self._career['season'].astype(int) <= last)].reset_index(drop=True).copy()

        # Change format of season column to work with the API
        season_df['season'] = season_df['season'].apply(lambda x: str(x) + "-" + str(x + 1)[2:])
        # Now create the df for the shot chart creation with the dfs given
        df = pd.DataFrame()
        for i in range(len(season_df)):
            log = shotchartdetail.ShotChartDetail(team_id=season_df.iloc[i]['Team ID'], player_id=self.player_id, \
             season_nullable=season_df.iloc[i]['season'], context_measure_simple=['FGA', 'FG3A'])
            df_1 = log.get_data_frames()[0]
            df_1['Season'] = season_df.iloc[i]['season']
            df = pd.concat([df, df_1])
        
        df.reset_index(inplace=True, drop=True)

        self._make_shot_chart(df)

    def _make_shot_chart(self, df):
        # This method will create the shot chart given a df created from the get_shot_chart method
        plt.figure(figsize=(12,11))
        plt.figure(figsize=(12,11))
        plt.scatter(df['LOC_X'], df['LOC_Y'], df['SHOT_MADE_FLAG'])
        draw_court(outer_lines=True)
        # Descending values along the axis from left to right
        plt.xlim(300,-300)
        plt.ylim(-100,500)
        plt.show()


class NBA_Season:
    def __init__(self, season=datetime.datetime.today().year - 1):
        '''
        Season object using data from basketball-reference.com

        Parameters:

        season (int, default: current year - 1)
            The season that you want to pull data from. 
                Ex. 2008
            If the season you inputted isn't an integer, a TypeError will be thrown.
        '''

        try:
            season = int(season)
        except:
            # This is probably because they inputted a string for season, and we need an int
            raise TypeError("Wrong variable type for season. Integer expected.")
        self.season = season
        self.season_str = str(season) + "-" + str(season + 1)[2:]

        # basketball-reference references the season by the second year in each season, so we need to add 1 to the season
        season = self.season + 1
        # The season goes from October to June usually, so we will go from July to June to capture all data
        months = [datetime.date(2019, i, 1).strftime('%B').lower() for i in list(range(7, 13)) + list(range(1,7))]

        # Getting the list of URLs with our months list
        urls = []
        for i in months:
            urls.append('https://www.basketball-reference.com/leagues/NBA_' + str(season) + '_games-' + str(i) + '.html')
        
        games = pd.DataFrame()
        for url in urls:
            try:
                month = pd.read_html(url)[0]
                month.drop(['Notes','Unnamed: 6'], axis=1, inplace=True)
                month.dropna(subset=['PTS'], inplace=True)
                games = pd.concat([games, month], sort=False)
            except:
                pass
        
        # Reset the index and rename the overtime column
        games.reset_index(inplace=True, drop=True)
        games.rename(columns={'Unnamed: 7': 'OT'}, inplace=True)

        self.games = games

        try:
            self.playoff_start = self.games[self.games['Date'] == 'playoffs'].index[0]
        except:
            # The specified season doeesn't contain playoff games
            self.playoff_start = None
    
    # Private method
    def __clean_games(self, df):
        df['Season'] = self.season_str
        df['Year'] = pd.to_datetime(df['Date']).dt.year
        df['PTS'] = df['PTS'].astype(int)
        df['PTS.1'] = df['PTS.1'].astype(int)
        df['MOV'] = abs(df['PTS'] - df['PTS.1'])
        df['Date'] = pd.to_datetime(df['Date'])
        df['Start (ET)'] = pd.to_datetime(df['Start (ET)'])
        df['OT'] = df['OT'].fillna('No overtime')
        return df
    
    def get_season(self):
        if self.playoff_start == None:
            return self.__clean_games(self.games.copy())
        else:
            return self.__clean_games(self.games[self.games.index < self.playoff_start].copy())
    
    def get_play(self):
        if self.playoff_start == None:
            raise SeasonNotFoundError("There are no play recorded for the " + self.season_str + " season.")
        else:
            return self.__clean_games(self.games[self.games.index > self.playoff_start].copy())

def thres_games(startyear=2000, endyear=datetime.datetime.today().year - 1, thres = 40):
    '''
    Returns a df detailing the number of games won by a number >= the threshold specified.

    Parameters:


    startyear (int, default: 2001)
        The first season that you want to be in the df.
            ex. 2015

    endyear (int, default: current year - 1)
        The last season that you want to be in the df.
            ex. 2019
    
    thres (int, default: 40)
        The margin of victory threshold for the df.
            ex. 30
    

    Returns:

    df
        A pd.DataFrame() containing the season data with the following columns:
            ['Season', 'Count', 'Game Nums', 'Projected']
            'Count' is the number of games over thres.
            'Projected' is for current seasons in play only.
    '''

    # Need to make sure that startyear, endyear and thres are all integers
    try:
        startyear = int(startyear)
        endyear = int(endyear)
        thres = int(thres)
    except:
        # This is probably because they inputted a string for season, and we need an int
        raise TypeError("Wrong variable type for startyear, endyear or thres. Integer expected.")
    # Need to check that endyear season exists
    try:
        # If there is data for endyear, we are good.
        Season(endyear)
    except:
        # If we can't get data from endyear, then raise SeasonNotFoundError
        raise SeasonNotFoundError("There is no data for the " + str(endyear) + " season yet.")

    years = [i for i in range(startyear, endyear + 1)]
    tot = []
    for i in years:
        curr_season = NBA_Season(i)
        year = curr_season.get_season()
        num_games = len(year)
        season = "'" +str(i)[2:] + " - '" + str(i + 1)[2:]
        game_nums = list(year[year['MOV'] >= thres].index + 1)
        year = year[year['MOV'] >= thres].copy()
        count = len(year)
        Projected = int(((count / num_games) * 1230) - count)
        tot.append([season, count, game_nums, Projected])
    
    return pd.DataFrame(tot, columns=['Season', 'Count', 'Game Nums', 'Projected'])

def draw_court(ax=None, color='black', lw=2, outer_lines=False):
    '''
    From http://savvastjortjoglou.com/nba-shot-sharts.html
    '''
    # If an axes object isn't provided to plot onto, just get current one
    if ax is None:
        ax = plt.gca()

    # Create the various parts of an NBA basketball court

    # Create the basketball hoop
    # Diameter of a hoop is 18" so it has a radius of 9", which is a value
    # 7.5 in our coordinate system
    hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)

    # Create backboard
    backboard = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color)

    # The paint
    # Create the outer box 0f the paint, width=16ft, height=19ft
    outer_box = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color,
                          fill=False)
    # Create the inner box of the paint, widt=12ft, height=19ft
    inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color,
                          fill=False)

    # Create free throw top arc
    top_free_throw = Arc((0, 142.5), 120, 120, theta1=0, theta2=180,
                         linewidth=lw, color=color, fill=False)
    # Create free throw bottom arc
    bottom_free_throw = Arc((0, 142.5), 120, 120, theta1=180, theta2=0,
                            linewidth=lw, color=color, linestyle='dashed')
    # Restricted Zone, it is an arc with 4ft radius from center of the hoop
    restricted = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw,
                     color=color)

    # Three point line
    # Create the side 3pt lines, they are 14ft long before they begin to arc
    corner_three_a = Rectangle((-220, -47.5), 0, 140, linewidth=lw,
                               color=color)
    corner_three_b = Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color)
    # 3pt arc - center of arc will be the hoop, arc is 23'9" away from hoop
    # I just played around with the theta values until they lined up with the 
    # threes
    three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw,
                    color=color)

    # Center Court
    center_outer_arc = Arc((0, 422.5), 120, 120, theta1=180, theta2=0,
                           linewidth=lw, color=color)
    center_inner_arc = Arc((0, 422.5), 40, 40, theta1=180, theta2=0,
                           linewidth=lw, color=color)

    # List of the court elements to be plotted onto the axes
    court_elements = [hoop, backboard, outer_box, inner_box, top_free_throw,
                      bottom_free_throw, restricted, corner_three_a,
                      corner_three_b, three_arc, center_outer_arc,
                      center_inner_arc]

    if outer_lines:
        # Draw the half court line, baseline and side out bound lines
        outer_lines = Rectangle((-250, -47.5), 500, 470, linewidth=lw,
                                color=color, fill=False)
        court_elements.append(outer_lines)

    # Add the court elements onto the axes
    for element in court_elements:
        ax.add_patch(element)

    return ax
