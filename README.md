# nba_vis

This project is where I keep all my files that I use when I analyze all sorts of NBA data.

## Files in this repository

__*margin_of_victory.py*__ - .py file with analysis that showed the '19 - '20 season is set to have the most 40-point blowouts of all time. [Here is my completed analysis.](https://www.tidbitstatistics.com/NBA-blowouts/)

__*nba_games.py*__ - .py file with methods and classes to help pull data from [basketball-reference.com](https://www.basketball-reference.com), [NPA API](https://github.com/swar/nba_api/), and other sources.

__*player_games.py*__ - .py file to pull a players game log for a season

__*.gitignore*__ - shows github what files to ignore when I commit my changes.

## TODO

- [ ] why are there so many blowouts this year? - create new .py file and dig in to it
- [ ] dig in to ppfta, ppfga, pp3pa on player_games.py
- [ ] add get_shot_chart() method to NBA_Player class
  - [x] pull data frames
  - [ ] create shot chart from data frames
    - [x] figure out fix, ax
    - [x] colors and background color
    - [x] limiters for the shots
    - [x] kwargs handling
    - [x] team_id df in \_\_init__ method
    - [x] add abbreviation functionality for get_shot_chart
    - [x] chart design
      - [x] add colorbar for hexbins
      - [x] hardwood floor? or other texture?
      - [x] legend as color scale
        - [x] move color ticks to percentile of cbar
    - [ ] determine zones
    - [ ] hex size as frequency
    - [ ] team logo on chart?
