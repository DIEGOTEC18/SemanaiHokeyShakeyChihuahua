""" Player module
This is a template/example class for your player.
This is the only file you should modify.
The logic of your hockey robot will be implemented in this class.
Please implement the interface next_move().
The only restrictions here are:
 - to implement a class constructor with the args: paddle_pos, goal_side
 - set self.my_display_name with your team's name, max. 15 characters
 - to implement the function next_move(self, current_state),
    returning the next position of your paddle
"""

import copy
import utils


class Player:
    def __init__(self, paddle_pos, goal_side):

        # set your team's name, max. 15 chars
        self.my_display_name = "ShakeyChihuahua"

        # these belong to my solution,
        # you may erase or change them in yours
        self.future_size = 30
        self.my_goal = goal_side
        self.my_goal_center = {}
        self.opponent_goal_center = {}
        self.my_paddle_pos = paddle_pos
        self.my_opponent_pos = {}
        self.my_goal_offset = 1.3
        self.goal_sideA = {}
        self.goal_sideB = {}

        # AI Modes: Attack (0) Defend (1) Evade (2)
        self.my_current_mode = 1
        self.elapsed_game_tiks = 0

    def next_move(self, current_state):
        """ Function that computes the next move of your paddle
        Implement your algorithm here. This will be the only function
        used by the GameCore. Be aware of abiding all the game rules.
        Returns:
            dict: coordinates of next position of your paddle.
        """

        # Insert classifier here:
        self.elapsed_game_tiks += 1

        # print(self.elapsed_game_tiks)
        self.classify(current_state, self.future_size)

        # update my paddle pos
        # I need to do this because GameCore moves my paddle randomly
        self.my_paddle_pos = current_state['paddle1_pos'] if self.my_goal == 'left' \
            else current_state['paddle2_pos']
        self.my_opponent_pos = current_state['paddle2_pos'] if self.my_goal == 'left' \
            else current_state['paddle1_pos']

        # estimate puck path
        path = estimate_path(current_state, self.future_size)

        # computing both goal centers
        self.my_goal_center = {'x': 0 if self.my_goal == 'left' else current_state['board_shape'][1],
                               'y': current_state['board_shape'][0] / 2}

        self.opponent_goal_center = {'x': 0 if self.my_goal == 'right' else current_state['board_shape'][1],
                                     'y': current_state['board_shape'][0] / 2}

        self.goal_sideA = {'x': self.my_goal_center['x'], 'y': (self.my_goal_center['y'] - (0.2 * 512))}
        self.goal_sideB = {'x': self.my_goal_center['x'], 'y': (self.my_goal_center['y'] + (0.2 * 512))}

        final_pos = self.attack(current_state)

        # find if puck path is inside my interest area
        roi_radius = current_state['board_shape'][0] * current_state['goal_size'] * self.my_goal_offset
        pt_in_roi = None
        for p in path:
            if utils.distance_between_points(p[0], self.my_goal_center) < roi_radius:
                pt_in_roi = p
                break

        if pt_in_roi:
            # print(final_pos)
            # estimate an aiming position

            if self.my_current_mode == 0:
                target_pos = utils.aim(pt_in_roi[0], pt_in_roi[1],
                                       final_pos, current_state['puck_radius'],
                                       current_state['paddle_radius'])

            # Defend:
            elif self.my_current_mode == 1:

                if (self.my_goal == "left"):
                    position = ((current_state['board_shape'][1] / 6) * 4)

                    if (current_state['puck_pos']['x'] > position):
                        target_pos = self.defend(current_state)

                    else:
                        target_pos = utils.aim(pt_in_roi[0], pt_in_roi[1],
                                               final_pos, current_state['puck_radius'],
                                               current_state['paddle_radius'])

                else:
                    position = ((current_state['board_shape'][1] / 6) * 2)
                    if (current_state['puck_pos']['x'] < position):
                        target_pos = self.defend(current_state)

                    else:
                        target_pos = utils.aim(pt_in_roi[0], pt_in_roi[1],
                                               final_pos, current_state['puck_radius'],
                                               current_state['paddle_radius'])
            # Evade:
            else:
                target_pos = self.evade(current_state)

            # move to target position, taking into account the max. paddle speed
            if target_pos != self.my_paddle_pos:
                direction_vector = {'x': target_pos['x'] - self.my_paddle_pos['x'],
                                    'y': target_pos['y'] - self.my_paddle_pos['y']}
                direction_vector = {k: v / utils.vector_l2norm(direction_vector)
                                    for k, v in direction_vector.items()}

                movement_dist = min(current_state['paddle_max_speed'] * current_state['delta_t'],
                                    utils.distance_between_points(target_pos, self.my_paddle_pos))
                direction_vector = {k: v * movement_dist
                                    for k, v in direction_vector.items()}
                new_paddle_pos = {'x': self.my_paddle_pos['x'] + direction_vector['x'],
                                  'y': self.my_paddle_pos['y'] + direction_vector['y']}

                # check if computed new position in not inside goal area
                # check if computed new position in inside board limits
                if utils.is_inside_goal_area_paddle(new_paddle_pos, current_state) is False and \
                        utils.is_out_of_boundaries_paddle(new_paddle_pos, current_state) is None:
                    self.my_paddle_pos = new_paddle_pos
        # time.sleep(2)
        # return {'x': -12, 'y': -6543}
        return self.my_paddle_pos

    '''def attack(self, current_state, after_time):

        state = copy.copy(current_state)
        max_dis = state['paddle_max_speed'] * after_time
        max_y = max_dis + self.my_opponent_pos['y']
        min_y = self.my_opponent_pos['y'] - max_y
        x_aim = (state['board_shape'][1] / 4) * 3
        # print(state['puck_pos'])
        if (self.my_opponent_pos['y'] > state['board_shape'][0] / 2):
            # print("Arriba")
            return {'x': x_aim, 'y': 0}
        else:
            # print("Abajo")
            return {'x': x_aim, 'y': state['board_shape'][0]}       
    '''

    def attack(self, current_state):
        state = copy.copy(current_state)

        length = state['board_shape'][0]
        Tx = self.my_paddle_pos['x']
        Tdy = length + self.my_paddle_pos['y']
        Tuy = -self.my_paddle_pos['y']
        self.opponent_goal_center = {'x': 0 if self.my_goal == 'right' else current_state['board_shape'][1],
                                     'y': current_state['board_shape'][0] / 2}
        Gy = self.opponent_goal_center['y']
        Gx = self.opponent_goal_center['x']

        t_maxA_puck = (utils.distance_between_points(state['puck_pos'], self.goal_sideA)) * (state['puck_speed']['y'])
        t_maxB_puck = (utils.distance_between_points(state['puck_pos'], self.goal_sideB)) * (state['puck_speed']['y'])
        t_max_paddle_A = utils.distance_between_points({'x': 0, 'y': self.my_opponent_pos['y']},
                                                       {'x': 0, 'y': self.goal_sideA['y']}) * state['paddle_max_speed']
        t_max_paddle_B = utils.distance_between_points({'x': 0, 'y': self.my_opponent_pos['y']},
                                                       {'x': 0, 'y': self.goal_sideB['y']}) * state['paddle_max_speed']

        '''if (state['puck_pos']['x'] < (state['board_shape'][1] / 2) and state['puck_pos']['x'] > self.my_paddle_pos[
            'x'] and self.my_goal == "left"):
            print("soy izquierdo")
            if (t_maxA_puck < t_max_paddle_A):
                print("apunta al extremo inferior directo")
                return {'x': state['board_shape'][1], 'y': self.goal_sideA['y'] + state['puck_radius']}
            if (t_maxB_puck < t_max_paddle_B):
                print("apunta al extremo superior directo")
                return {'x': state['board_shape'][1], 'y': self.goal_sideB['y'] - state['puck_radius']}
        elif (state['puck_pos']['x'] > (state['board_shape'][1] / 2) and state['puck_pos']['x'] < self.my_paddle_pos[
            'x'] and self.my_goal == "right"):
            print("soy derecho")
            if (t_maxA_puck < t_max_paddle_A):
                print("apunta al extremo inferior directo")
                print({'x': 0, 'y': self.goal_sideA['y'] + state['puck_radius']})
                return {'x': 0, 'y': self.goal_sideA['y'] + state['puck_radius']}
            if (t_maxB_puck < t_max_paddle_B):
                print("apunta al extremo superior directo")
                print({'x': 0, 'y': self.goal_sideB['y'] - state['puck_radius']})
                return {'x': 0, 'y': self.goal_sideB['y'] - state['puck_radius']}'''

        if (self.my_opponent_pos['y'] <= (length / 2)):
            print("Abajo")
            return {'x': ((length - Tdy) / ((Tdy - Gy) / (Tx - Gx))) + Tx, 'y': length}
        else:
            print("Arriba")
            return {'x': ((length - Tuy) / ((Tuy - Gy) / (Tx - Gx))) + Tx, 'y': 0}

    # Defend Function:
    def defend(self, current_state):

        offset = 1
        state = copy.copy(current_state)
        self.my_goal_offset = offset
        rad = (state['goal_size'] * state['board_shape'][0]) / 2

        ofup = (state['board_shape'][0] / 2) - (state['board_shape'][0] * 0.7)
        ofdown = (state['board_shape'][0] / 2) + (state['board_shape'][0] * 0.7)

        if (self.my_goal == "left"):
            if state['puck_pos']['x'] < self.my_opponent_pos['x']:

                if state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    print("soy izquierdo y estoy defendiendo arriba")
                    # print("Es en el 2 if")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    print("soy izquierda y estoy defendiendo arriba")
                    # print("Es en el 1 elif")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    print("soy izquierda y estoy defendiendo abajo")
                    # print("Es en el 2 elif")

                    return {'x': rad, 'y': ofdown}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    print("soy izquierda y estoy defendiendo abajo")
                    # print("Es en el 3 elif")

                    return {'x': rad, 'y': ofdown}

                else:

                    # print("Es en el 1 else")
                    return {'x': rad, 'y': state['board_shape'][0] / 2}

            else:

                print("Está adelante el oponente")
                return {'x': rad, 'y': state['board_shape'][0] / 2}

        if (self.my_goal == "right"):
            if state['puck_pos']['x'] > self.my_opponent_pos['x']:

                if state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    print("soy derecha y estoy defendiendo arriba")
                    # print("Es en el 2 if")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    print("soy derecha y estoy defendiendo arriba")
                    # print("Es en el 1 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofup}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    print("soy derecha y estoy defendiendo abajo")
                    # print("Es en el 2 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofdown}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    print("soy derecha y estoy defendiendo abajo")
                    # print("Es en el 3 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofdown}

                else:

                    # print("Es en el 1 else")
                    return {'x': state['board_shape'][0] - rad, 'y': state['board_shape'][0] / 2}

            else:

                print("Está adelante el oponente")
                return {'x': state['board_shape'][0] - rad, 'y': state['board_shape'][0] / 2}

        # print(self.my_paddle_pos)

        # return {'x': state['board_shape'][1] / 5, 'y': state['board_shape'][0] / 5}

    # Classifier:
    def classify(self, current_state, after_time):

        state = copy.copy(current_state)

        # Protección anti-autogol:
        if (self.my_goal == "left"):
            if state['puck_pos']['x'] < (self.my_paddle_pos['x']) and self.my_current_mode != 1:
                print("soy izquierdo y hay Riesgo de autogol")
                self.my_current_mode = 2
            else:

                self.my_current_mode = 1
        else:
            if state['puck_pos']['x'] > (self.my_paddle_pos['x']) and self.my_current_mode != 1:
                print("soy derecho y hay Riesgo de autogol")
                self.my_current_mode = 2
            else:
                self.my_current_mode = 1

    # Evade:
    def evade(self, current_state):

        state = copy.copy(current_state)

        return self.my_paddle_pos


def estimate_path(current_state, after_time):
    """ Function that function estimates the next moves in a after_time window
    Returns:
        list: coordinates and speed of puck for next ticks
    """

    state = copy.copy(current_state)
    path = []
    while after_time > 0:
        state['puck_pos'] = utils.next_pos_from_state(state)
        if utils.is_goal(state) is not None:
            break
        if utils.next_after_boundaries(state):
            state['puck_speed'] = utils.next_after_boundaries(state)
        path.append((state['puck_pos'], state['puck_speed']))
        after_time -= state['delta_t']
    return path