#!/usr/bin/python

from __future__ import print_function

import sys
import random

import pacmanclient as pc


class MyPacmanStrategy(pc.PlayerStrategy):

    def __init__(self, team_name):
        self._team_name = team_name

    def play_turn(self, turn_info):
        """ Return a direction as a string.

        I.e. one of the following strings: 'UP', 'RIGHT', 'DOWN', 'LEFT'."""

        # TODO Implement your pacman move algorithm here.

        # Get our player information.
        my_team = [team for team in turn_info.teams
                if team.name == self._team_name]
        pacman = my_team[0].pacman
        x = pacman.x
        y = pacman.y
        mapInfo = turn_info.map

        # Do not go towards walls.
        possible_moves = []
        if not mapInfo.is_wall(x + 1, y):
            possible_moves.append('RIGHT')
        if not mapInfo.is_wall(x - 1, y):
            possible_moves.append('LEFT')
        if not mapInfo.is_wall(x, y + 1):
            possible_moves.append('UP')
        if not mapInfo.is_wall(x, y - 1):
            possible_moves.append('DOWN')

        # Prevent turn backs when possible.
        if possible_moves > 1:
            opposite_dict = {None: None,
                    'NONE': None,
                    'RIGHT': 'LEFT',
                    'LEFT': 'RIGHT',
                    'UP': 'DOWN',
                    'DOWN': 'UP'}
            opposite = opposite_dict[pacman.previous_move]
            if opposite is not None and opposite in possible_moves:
                possible_moves.remove(opposite)

        return random.choice(possible_moves)


class MyGhostStrategy(pc.PlayerStrategy):

    def __init__(self, team_name):
        self._team_name = team_name

    def play_turn(self, turn_info):
        """ Return a direction as a string.

        I.e. one of the following strings: 'UP', 'RIGHT', 'DOWN', 'LEFT'."""

        # TODO Implement your pacman move algorithm here.

        return random.choice(['UP', 'RIGHT', 'DOWN', 'LEFT'])


def main(argv=None):

    # Required information.
    LOGIN = 'test'
    PASSWORD = 'test'
    TEAM_NAME = 'Py Team'
    PACMAN_NAME = 'PyPac'
    GHOST_NAME = 'PyGhost'
    TOURNAMENT_ID = 'test3'
    #pc.URL_BASE = 'http://<non-default.url>/rootpath'  # If needed only.

    # Setup your team and players.
    #
    # More precisely, setup your own algorithm
    # for your ghost and pacman.
    my_client = pc.PacmanClient(TEAM_NAME, PACMAN_NAME, GHOST_NAME)
    my_client.pacman.strategy = MyPacmanStrategy(TEAM_NAME)
    my_client.ghost.strategy = MyGhostStrategy(TEAM_NAME)

    # Log to the game server.
    print('Login as', LOGIN)
    my_client.login(LOGIN, PASSWORD)

    # Join and wait until tournament is played.
    print('Joining tournament', TOURNAMENT_ID)
    my_client.play_tournament(TOURNAMENT_ID)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
