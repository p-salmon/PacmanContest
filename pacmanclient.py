#!/usr/bin/python

from __future__ import print_function

import sys
import random
import json

try:
    import requests
except ImportError:
    print('Do yourself a sweet favor: install "requests" package')
    sys.exit(1)


# Setup default URL.
URL_BASE = 'http://80.12.13.121/backend'


class PacmanClient:

    def __init__(self, team_name, pacman_name, ghost_name):
        self.session = None
        self.team_name = team_name
        self.pacman = Pacman({"name": pacman_name})
        self.ghost = Ghost({"name": ghost_name})

    def login(self, username, password):
        self.username = username
        self.password = password

        self.session = requests.session()

        login_url = URL_BASE + '/login?user={username}&password={password}' \
                .format(username=username, password=password)
        print('Logging to game server with GET ' + login_url)
        r = self.session.get(login_url, allow_redirects=True)
        if r.status_code != 200:
            print('ERROR: Login request failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception

        print('Logged with token ' + self.session.cookies['JSESSIONID'])

    def join_game(self, game_id):
        self.pacman.join_game(self.session, self.team_name, game_id)
        self.ghost.join_game(self.session, self.team_name, game_id)

    def play_turn(self, game_id, turn):
        self.pacman.play_turn(self.session, game_id, turn)
        self.ghost.play_turn(self.session, game_id, turn)

    def play_tournament(self, tournament_id):
        # Join tournament.
        tournament = Tournament.join(self, tournament_id)

        # Look for next game in tournament.
        game = tournament.get_next_game(self)
        #for game in tournament.games(self):  # TODO Use a generator
        while game is not None:

            # Join and play next game.
            game.join(self)
            game.play()

            # Look for next game in tournament.
            game = tournament.get_next_game(self)


class PlayerStrategy:

    def play_turn(self, turn):
        pass


class DefaultPlayerStrategy(PlayerStrategy):

    def play_turn(self, turn):
        return random.choice(['UP', 'RIGHT', 'DOWN', 'LEFT'])


class Player:

    def __init__(self, json_obj):
        self.name = json_obj['name']

        try:
            self.status = json_obj['status']
        except KeyError:
            self.status = None

        try:
            position = json_obj['position']
            self.x = position['column']
            self.y = position['line']
        except KeyError:
            self.x = None
            self.y = None

        try:
            self.previous_move = json_obj['move']
        except KeyError:
            self.previous_move = None

        try:
            self.dead = json_obj['dead']
        except KeyError:
            self.dead = False

    def join_game(self, session, team_name, game_id):
        join_url = '{url_base}/players/{playerName}' \
                '/game/{gameId}'\
                .format(url_base=URL_BASE,
                        playerName=self.name,
                        gameId=game_id)
        print('Joining game with POST {url}'.format(url=join_url))
        r = session.post(join_url)
        if r.status_code != 200:
            print('ERROR: Join game request failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception

    def _choose_direction(self, turn):
        try:
            strategy = self.strategy
        except AttributeError:
            self.strategy = DefaultPlayerStrategy()
            strategy = self.strategy
        return strategy.play_turn(turn)

    def play_turn(self, session, game_id, turn):
        # Choose direction.
        move = self._choose_direction(turn)

        # Send result.
        play_url = '{url_base}/players/{playerName}' \
                '/game/{gameId}/turn/{turnId}/move/{move}'\
                .format(url_base=URL_BASE,
                        playerName=self.name,
                        gameId=game_id,
                        turnId=turn.turn_number,
                        move=move)
        print('Playing turn with POST {url}'.format(url=play_url))
        r = session.post(play_url)
        if r.status_code != 200:
            print('ERROR: Play turn request failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception


class Pacman(Player):

    def __str__(self):
        return '<Pacman name={0.name} status={0.status} x={0.x} y={0.y} ' \
                'previous_move={0.previous_move} dead={0.dead}>'.format(self)


class Ghost(Player):

    def __str__(self):
        return '<Ghost name={0.name} status={0.status} x={0.x} y={0.y} ' \
                'previous_move={0.previous_move}>'.format(self)


class Team:

    def __init__(self, json_obj):
        self.score = json_obj['score']
        self.name = json_obj['teamName']
        self.pacman = Pacman(json_obj['pacman'])
        self.ghost = Ghost(json_obj['ghost'])

    def __str__(self):
        return '<Team name={0.name} score={0.score}\n' \
                'pacman={0.pacman}\nghost={0.ghost}\n>'.format(self)


class Game:

    def __init__(self, json_obj, user):
        self._update_information(json_obj)
        self._user = None
        self._joined = False

    def _update_information(self, json_obj):
        self.winning_team = json_obj['winningTeam']
        self.game_id = json_obj['id']
        self.expected_team_count = json_obj['expectedTeamCount']
        self.current_turn_number = json_obj['currentTurn']
        self.status = json_obj['gameStatus']
        self.map_id = json_obj['mapName']

        self.teams = []
        for team_obj in json_obj['teams']:
            self.teams.append(Team(team_obj))

    def join(self, user):
        user.join_game(self.game_id)
        print('Joined game "{game}"'.format(game=self.game_id))
        self._joined = True
        self._user = user

    def play(self):
        if not self._joined:
            print('ERROR: You must join a game before playing it')
            raise Exception

        # Assume game status is 'READY'.
        # First turn will make us wait
        # until the game is really started.
        played_turn_number = int(self.current_turn_number)
        while True:
            # Get turn information.
            played_turn = Turn.get_turn(self._user,
                    self.game_id,
                    played_turn_number)

            if played_turn.last_turn:
                print("Turn {} was last turn of game {}".format(
                    played_turn.turn_number, self.game_id))
                return

            # Let players choose their moves.
            self._user.play_turn(self.game_id, played_turn)

            played_turn_number += 1

    def __str__(self):
        return '<Game game_id={o.game_id} status={o.status} ' \
                'expected_team_count={o.expected_team_count} ' \
                'current_turn_number={o.current_turn_number} ' \
                'winning_team={o.winning_team}  map_id={o.map_id} ' \
                'teams={o.teams}\n>'.format(o=self)


class Turn:

    def __init__(self, json_obj):
        self.turn_number = json_obj['turnNumber']
        self.last_turn = json_obj['lastTurn']

        self.teams = []
        for team_obj in json_obj['teams']:
            self.teams.append(Team(team_obj))

        self.map = Map(json_obj['map'])

    @classmethod
    def get_turn(cls, user, game_id, turn_id):
        turn_url = '{url_base}/games/{gameId}/turn/{turnId}' \
                .format(url_base=URL_BASE,
                        gameId=game_id,
                        turnId=turn_id)
        print('Looking for turn with GET {url}'.format(url=turn_url))

        retries = 0
        while True:
            r = user.session.get(turn_url)

            if r.status_code != 404:
                if retries > 0:
                    print(' OK')  # Add EOL missing from previous print call.
                break

            if retries == 0:
                print('Waiting for turn {} to be available'.format(turn_id),
                        end='')
            else:
                print('.', end='')
            sys.stdout.flush()
            retries += 1

        if r.status_code != 200:
            print('ERROR: Get turn request failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception

        return cls(r.json())

    def __str__(self):
        teams = '\n'.join(str(team) for team in self.teams)
        return '<Turn turn_number={o.turn_number} last_turn={o.last_turn}\n' \
                'teams=\n{teams}\nmap={o.map}>'.format(o=self, teams=teams)


class Map:

    def __init__(self, json_obj):
        self._raw_map = json_obj

    def is_wall(self, x, y):
        return self._raw_map[y][x] == 'X'

    def is_pacgum(self, x, y):
        return self._raw_map[y][x] == 'O'

    def __str__(self):
        o = self._raw_map
        return '<Map size: {}x{}, details: {}\n>'.format(len(o[0]), len(o),
                json.dumps(o, indent=4))


class Tournament:

    def __init__(self, name):
        self.name = name

    @classmethod
    def join(cls, user, name):
        join_url = '{url_base}/tournaments/{tournament}/team/{team}' \
                '?pacmanName={pacman}&ghostName={ghost}' \
                .format(url_base=URL_BASE,
                        tournament=name,
                        team=user.team_name,
                        pacman=user.pacman.name,
                        ghost=user.ghost.name)
        print('Joining tournament "{tournament_name}" with POST {url}' \
                .format(tournament_name=name, url=join_url))
        r = user.session.post(join_url)
        if r.status_code != 200:
            print('ERROR: Join tournament req failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception

        print('Joined tournament "{tournament}"' \
                .format(tournament=name))
        return cls(name)

    def get_next_game(self, user):
        next_game_url = '{url_base}/tournaments/{tournament}' \
                '/team/{team}/game' \
                .format(url_base=URL_BASE,
                        tournament=self.name,
                        team=user.team_name)
        print('Looking for next game with GET {url}'.format(url=next_game_url))

        retries = 0
        while True:
            r = user.session.get(next_game_url)

            if r.status_code != 404:
                if retries > 0:
                    print(' OK')  # Add EOL missing from previous print call.
                break

            if retries == 0:
                print('Waiting for next game to be available', end='')
            else:
                print('.', end='')
            sys.stdout.flush()
            retries += 1

        #if r.status_code == XXX: #TODO
            #print('Server tells that tournament is over for us')
            #return None

        if r.status_code != 200:
            print('ERROR: Get next game req failed with status {status}:\n' \
                    '{content}'
                    .format(status=r.status_code, content=r.text))
            raise Exception

        game = Game(r.json(), user)
        if game.current_turn_number is None:
            game.current_turn_number = '0'  # FIXME: Should be set.
        print('Next game Id is "{game_id}"'.format(game_id=game.game_id))
        return game


def main(argv=None):

    def parse_cmd_line():
        TEAM_NAME = 'My team'
        PACMAN_NAME = 'My pacman'
        GHOST_NAME = 'My ghost'
        DEFAULT_LOGIN = 'test'
        DEFAULT_PASSWORD = 'test'

        import argparse
        parser = argparse.ArgumentParser(
                description='Simple Pacman Coding contest client',
                epilog='Note that this client is rather dumb, ' \
                        'you should be able to play better than ' \
                        'its default implementation.')
        parser.add_argument('server_url', nargs='?', default=URL_BASE,
                help='Server URL, e.g. http://gameserver.com/cc2013')
        parser.add_argument('--team', default=TEAM_NAME,
                help='declared team name', metavar='NAME')
        parser.add_argument('--pacman', default=PACMAN_NAME,
                help='declared pacman name', metavar='NAME')
        parser.add_argument('--ghost', default=GHOST_NAME,
                help='declared ghost name', metavar='NAME')
        parser.add_argument('--login', default=DEFAULT_LOGIN,
                help='your game server account login')
        parser.add_argument('--password', default=DEFAULT_PASSWORD,
                help='your game server account password')
        parser.add_argument('--tournament', '-t',
                required=True, metavar='NAME')
        return parser.parse_args()

    args = parse_cmd_line()
    print("""Starting Pacman game client with the following parameters:
    server location\t{0.server_url}
    Team name\t\t{0.team}
    Pacman name\t\t{0.pacman}
    Ghost name\t\t{0.ghost}
    Tournament name\t{0.tournament}
    User login\t\t{0.login}
    User password\t{0.password}
""".format(args))

    # Deal with server URL.
    global URL_BASE
    URL_BASE = args.server_url

    # Create team and players, but keep default strategy.
    client = PacmanClient(args.team, args.pacman, args.ghost)

    # Log to game server.
    client.login(args.login, args.password)

    # Join and play tournament.
    client.play_tournament(args.tournament)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
