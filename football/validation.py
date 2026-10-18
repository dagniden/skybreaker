"""Version 1 data-only contract, shared with the Godot recorder/legacy viewer."""
import math

MAX_BYTES = 12 * 1024 * 1024
MAX_FRAMES = 12002
MAX_DURATION_MS = 600000


def number(value, minimum, maximum):
    return type(value) in (int, float) and minimum <= value <= maximum and math.isfinite(value)


def validate_replay(data):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1 or data.get('mode') != 'free_play' or data.get('field') != [1600, 900]:
        raise ValueError('Unsupported replay format')
    units = data.get('units')
    if not isinstance(units, list) or len(units) != 12:
        raise ValueError('Expected twelve players')
    for team in (0, 1):
        members = [u for u in units if isinstance(u, dict) and type(u.get('team')) is int and u['team'] == team]
        if len(members) != 6 or any(type(u.get('keeper')) is not bool for u in members) or sum(u['keeper'] for u in members) != 1:
            raise ValueError('Invalid team roster')
    frames = data.get('frames')
    if not isinstance(frames, list) or not 2 <= len(frames) <= MAX_FRAMES:
        raise ValueError('Invalid frame count')
    previous_time, previous_round = -1, 0
    previous_score = [0, 0]
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError('Invalid frame')
        stamp, positions, ball = frame.get('t'), frame.get('u'), frame.get('b')
        if type(stamp) is not int or not previous_time < stamp <= MAX_DURATION_MS:
            raise ValueError('Frame times must increase')
        if previous_time == -1 and stamp != 0:
            raise ValueError('Replay must begin at zero')
        if not isinstance(positions, list) or len(positions) != len(units):
            raise ValueError('Invalid player positions')
        for position in positions:
            if not isinstance(position, list) or len(position) != 4 or not all(number(v, -10000, 10000) for v in position[:2]) or not all(number(v, -1.01, 1.01) for v in position[2:]):
                raise ValueError('Invalid player coordinates')
        if not isinstance(ball, list) or len(ball) != 2 or not all(number(v, -10000, 10000) for v in ball):
            raise ValueError('Invalid ball coordinates')
        holder, score, round_id = frame.get('h'), frame.get('s'), frame.get('r')
        if type(holder) is not int or not -1 <= holder < len(units):
            raise ValueError('Invalid ball holder')
        if not isinstance(score, list) or len(score) != 2 or not all(type(v) is int and 0 <= v <= 10000 for v in score) or any(score[i] < previous_score[i] for i in (0, 1)):
            raise ValueError('Invalid score')
        if type(round_id) is not int or not previous_round <= round_id <= 10000:
            raise ValueError('Invalid round')
        previous_time, previous_round, previous_score = stamp, round_id, score
    if type(data.get('duration_ms')) is not int or data['duration_ms'] != previous_time:
        raise ValueError('Duration does not match recording')
    return {'version': 1, 'mode': 'free_play', 'field': [1600, 900],
            'units': [{'team': u['team'], 'keeper': u['keeper']} for u in units],
            'duration_ms': previous_time,
            'frames': [{k: f[k] for k in ('t', 'u', 'b', 'h', 's', 'r')} for f in frames]}
