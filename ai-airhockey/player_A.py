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

        # intialize limits of opponent's goal
        self.goal_sideA = {}
        self.goal_sideB = {}

        # AI Modes: Attack (0) Defend (1) Evade (2)
        self.my_current_mode = 1

        self.elapsed_game_tiks = 0

        self.quick_off = 0
        self.my_last_mode = 0

        # Logs:

        self.opponent_distances_from_goal = []
        self.opponent_shots_to_goal = 0
        self.puck_last_x = 0
        self.puck_last_y = 0
        self.puck_crossed = 0

    def next_move(self, current_state):
        """ Function that computes the next move of your paddle
        Implement your algorithm here. This will be the only function
        used by the GameCore. Be aware of abiding all the game rules.
        Returns:
            dict: coordinates of next position of your paddle.
        """



        self.elapsed_game_tiks += 1

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

        #Assign value to sides of opponent's goal
        self.goal_sideA = {'x': self.my_goal_center['x'], 'y': (self.my_goal_center['y'] - (0.2 * 512))}
        self.goal_sideB = {'x': self.my_goal_center['x'], 'y': (self.my_goal_center['y'] + (0.2 * 512))}

        # Logs go here:

        # Log the distance of the opponent to its goal:
        opponent_distance_from_goal = 0

        lower_extreme = (current_state['board_shape'][0] / 2) - ((current_state['board_shape'][0] * current_state['goal_size']) / 2)

        higher_extreme = (current_state['board_shape'][0] / 2) + ((current_state['board_shape'][0] * current_state['goal_size']) / 2)

        # Determine if the last shot was to the goal:
        if self.my_goal == 'left':
            if self.puck_last_x > current_state['puck_pos']['x'] and current_state['puck_pos']['y'] > lower_extreme and \
                    current_state['puck_pos']['y'] < higher_extreme and current_state['puck_pos']['x'] < (current_state['board_shape'][1] / 3) and self.puck_crossed == 0:

                self.opponent_shots_to_goal += 1  # Its a shot to our goal
                self.puck_crossed = 1

        else:
            if self.puck_last_x < current_state['puck_pos']['x'] and current_state['puck_pos']['y'] > lower_extreme and \
                    current_state['puck_pos']['y'] < higher_extreme and current_state['puck_pos']['x'] > ((current_state['board_shape'][1] / 3) * 2) and self.puck_crossed == 0:

                self.opponent_shots_to_goal += 1  # Its a shot to our goal
                self.puck_crossed = 1


        if self.my_goal == 'left':
           opponent_distance_from_goal = current_state['board_shape'][1] - self.my_opponent_pos['x']

           if self.puck_last_x < current_state['puck_pos']['x'] and current_state['puck_pos']['x'] > (current_state['board_shape'][1] / 2):
               self.puck_crossed = 0


        else:
            opponent_distance_from_goal = self.my_opponent_pos['x']

            if self.puck_last_x > current_state['puck_pos']['x'] and current_state['puck_pos']['x'] < (
                    current_state['board_shape'][1] / 2):
                self.puck_crossed = 0

        self.opponent_distances_from_goal.append(opponent_distance_from_goal)

        self.puck_last_x = current_state['puck_pos']['x']


        # print(path)

        # Determine if a shot was aiming to the goal:


        # Classify based on logs:
        self.classify(current_state, self.future_size)

        self.puck_last_y = current_state['puck_pos']['y']

        # Attack:

        final_pos = self.attack(current_state)

        # find if puck path is inside my interest area
        roi_radius = current_state['board_shape'][0] * current_state['goal_size'] * self.my_goal_offset
        pt_in_roi = None
        for p in path:
            if utils.distance_between_points(p[0], self.my_goal_center) < roi_radius or self.quick_off == 1:
                pt_in_roi = p
                break

        #print("Pt:")
        #print(pt_in_roi)

        if pt_in_roi:
            # print(final_pos)
            # estimate an aiming position

            # Attack:
            if self.my_current_mode == 0:

                self.my_goal_offset = 1.3

                target_pos = utils.aim(pt_in_roi[0], pt_in_roi[1],
                                    final_pos, current_state['puck_radius'],
                                    current_state['paddle_radius'])

            # Defend:
            elif self.my_current_mode == 1:
                if (self.my_goal == "left"):
                    position = ((current_state['board_shape'][1] / 6) * 4)

                    if current_state['puck_pos']['x'] > ((current_state['board_shape'][1] / 6) * 4):

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
            # print(target_pos)

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

        if (self.my_opponent_pos['y'] <= length / 2):
            # print("Abajo")
            return {'x': ((length - Tdy) / ((Tdy - Gy) / (Tx - Gx))) + Tx, 'y': length}
        else:
            # print("Arriba")
            return {'x': ((length - Tuy) / ((Tuy - Gy) / (Tx - Gx))) + Tx, 'y': 0}

    # Defend Function:

    def defend(self, current_state):
        offset = 1
        state = copy.copy(current_state)
        self.my_goal_offset = offset
        rad = (state['goal_size'] * state['board_shape'][0]) / 2

        ofup = (state['board_shape'][0] / 2) - (state['board_shape'][0] * 0.7)
        ofdown = (state['board_shape'][0] / 2) + (state['board_shape'][0] * 0.7)

        lower_extreme = (current_state['board_shape'][0] / 2) - (
                    (current_state['board_shape'][0] * current_state['goal_size']) / 2)

        higher_extreme = (current_state['board_shape'][0] / 2) + (
                    (current_state['board_shape'][0] * current_state['goal_size']) / 2)

        if (self.my_goal == "left"):
            if state['puck_pos']['x'] < self.my_opponent_pos['x']:

                if state['puck_pos']['y'] > lower_extreme and state['puck_pos']['y'] < higher_extreme and self.my_opponent_pos['y'] > lower_extreme and self.my_opponent_pos['y'] < higher_extreme:

                    return {'x': ((state['goal_size'] * state['board_shape'][0]) / 2) + (state['board_shape'][1] * 0.05), 'y': (state['board_shape'][0] / 2)}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy izquierdo y estoy defendiendo arriba")
                    # print("Es en el 2 if")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy izquierda y estoy defendiendo arriba")
                    # print("Es en el 1 elif")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy izquierda y estoy defendiendo abajo")
                    # print("Es en el 2 elif")

                    return {'x': rad, 'y': ofdown}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy izquierda y estoy defendiendo abajo")
                    # print("Es en el 3 elif")

                    return {'x': rad, 'y': ofdown}

                else:

                    # print("Es en el 1 else")
                    return {'x': rad, 'y': state['board_shape'][0] / 2}

            else:

                # print("Está adelante el oponente")
                return {'x': rad, 'y': state['board_shape'][0] / 2}

        if (self.my_goal == "right"):
            if state['puck_pos']['x'] > self.my_opponent_pos['x']:

                if state['puck_pos']['y'] > lower_extreme and state['puck_pos']['y'] < higher_extreme and self.my_opponent_pos['y'] > lower_extreme and self.my_opponent_pos['y'] < higher_extreme:

                    print("Defiende EN MEDIO")

                    return {'x': (state['board_shape'][1]) - ((state['goal_size'] * (state['board_shape'][0]) / 2) + (
                                state['board_shape'][1] * 0.05)),
                            'y': (state['board_shape'][0] / 2)}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy derecha y estoy defendiendo arriba")
                    # print("Es en el 2 if")

                    return {'x': rad, 'y': ofup}

                elif state['puck_pos']['y'] > (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy derecha y estoy defendiendo arriba")
                    # print("Es en el 1 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofup}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] < \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy derecha y estoy defendiendo abajo")
                    # print("Es en el 2 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofdown}

                elif state['puck_pos']['y'] < (state['board_shape'][0] / 2) and state['puck_pos']['y'] > \
                        self.my_opponent_pos[
                            'y']:
                    # print("soy derecha y estoy defendiendo abajo")
                    # print("Es en el 3 elif")

                    return {'x': state['board_shape'][0] - rad, 'y': ofdown}

                else:

                    # print("Es en el 1 else")
                    return {'x': state['board_shape'][0] - rad, 'y': state['board_shape'][0] / 2}

            else:

                # print("Está adelante el oponente")
                return {'x': state['board_shape'][0] - rad, 'y': state['board_shape'][0] / 2}

        # print(self.my_paddle_pos)

        # return {'x': state['board_shape'][1] / 5, 'y': state['board_shape'][0] / 5}

    #Classifier:
    def classify(self, current_state, after_time):

        state = copy.copy(current_state)

        losing = False

        #print(self.my_goal)

        if self.quick_off == 1:
            self.my_current_mode = 1
            self.quick_off = 0

        if self.my_goal == 'left':

            if state['goals']['left'] < state['goals']['right']:
                losing = True

            if state['is_goal_move'] is not None and state['puck_pos']['x'] < (state['board_shape'][1] / 2):

                print("Sacamos de nuestra cancha")

                self.my_current_mode = 0
                self.quick_off = 1

            elif state['is_goal_move'] is not None and state['puck_pos']['x'] > (state['board_shape'][1] / 2):
                print("Borrar posiblemente")
                self.my_current_mode = 1
                self.quick_off = 0

            else:
                self.quick_off = 0

        else:

            if state['goals']['left'] > state['goals']['right']:
                losing = True

            if state['is_goal_move'] is not None and state['puck_pos']['x'] > (state['board_shape'][1] / 2):

                print("Sacamos de nuestra cancha")

                self.quick_off = 1
                self.my_current_mode = 0

            elif state['is_goal_move'] is not None and state['puck_pos']['x'] < (state['board_shape'][1] / 2):
                print("NUNCA ENTRA AQUÍ")
                self.my_current_mode = 1
                self.quick_off = 0

            else:
                self.quick_off = 0

        # Protección anti-autogol:
        if self.my_goal == "left" and state['puck_pos']['x'] < (self.my_paddle_pos['x']) and self.my_current_mode != 1:
                print("soy izquierdo y hay Riesgo de autogol")
                self.my_current_mode = 2
        elif state['puck_pos']['x'] > (self.my_paddle_pos['x']) and self.my_current_mode != 1 and self.my_goal=="right":
                print("soy derecho y hay Riesgo de autogol")
                self.my_current_mode = 2

        # Update tactics:
        if self.elapsed_game_tiks % 50 == 0:
            distance_sum = 0.0

            for i in range(0, len(self.opponent_distances_from_goal)):
                distance_sum += self.opponent_distances_from_goal[i]

            average = distance_sum / len(self.opponent_distances_from_goal)

            print("Elapsed ticks:")
            print(self.elapsed_game_tiks)

            print("The average is:")
            print(average)
            # print("Number of elements:")
            # print(len(self.opponent_distances_from_goal))
            # print(self.my_current_mode)
            print("Shots to goal:")
            print(self.opponent_shots_to_goal)

            if average > (state['board_shape'][1] / 5) and self.opponent_shots_to_goal > 3:
                print("The opponent is in an ofense position")

                self.my_last_mode = self.my_current_mode
                self.my_current_mode = 1

            elif average > (state['board_shape'][1] / 5) and self.opponent_shots_to_goal < 3:
                print("The opponent is in a line position")

                self.my_last_mode = self.my_current_mode
                self.my_current_mode = 0

            elif average < (state['board_shape'][1] / 5) and self.opponent_shots_to_goal > 3:
                print("The opponent is in a defense position but aiming to goal")

                if losing:
                    print("...but we are losing")

                    self.my_last_mode = self.my_current_mode
                    self.my_current_mode = 1

                else:
                    print("...but we are winning")

                    self.my_last_mode = self.my_current_mode
                    self.my_current_mode = 0

            elif average < (state['board_shape'][1] / 5) and self.opponent_shots_to_goal < 3:
                print("The opponent is in a defense position")

                if losing:
                    print("...but we are losing")

                    if self.elapsed_game_tiks % 100 == 0 and self.my_last_mode == 1:
                        self.my_last_mode = self.my_current_mode
                        self.my_current_mode = 0

                        print("AAAAAAHHHHHHH")

                    else:

                        self.my_last_mode = self.my_current_mode
                        self.my_current_mode = 1


                else:
                    print("...but we are winning")

                    self.my_last_mode = self.my_current_mode
                    self.my_current_mode = 0

            print("Decided mode:")
            print(self.my_current_mode)

            # Erase logs:
            self.opponent_distances_from_goal = []

            if self.elapsed_game_tiks % 500 == 0:

                print("Goal counter reset")
                self.opponent_shots_to_goal = 0

    # Evade:
    def evade(self, current_state):

        state = copy.copy(current_state)

        # return self.my_paddle_pos

        ''' It makes it easier for the opponent to strike.
        if state['puck_pos']['y'] < self.puck_last_y:
            # Va hacia arriba
            return {'x': self.my_paddle_pos['x'], 'y': (state['board_shape'][0] / 2) + state['puck_pos']['y']}

        else:
            # Va hacia abajo
            return {'x': self.my_paddle_pos['x'], 'y': (state['board_shape'][0] / 2) - (state['puck_pos']['y'] - (state['board_shape'][0] / 2))}
        '''

        if self.my_goal == 'left':

            return {'x': ((state['goal_size'] * state['board_shape'][0]) / 2) + (state['board_shape'][1] * 0.05), 'y' : (state['board_shape'][0] / 2)}

        else:

            return {'x': (state['board_shape'][1]) - ((state['goal_size'] * (state['board_shape'][0]) / 2) + (state['board_shape'][1] * 0.05)),
                    'y': (state['board_shape'][0] / 2)}


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