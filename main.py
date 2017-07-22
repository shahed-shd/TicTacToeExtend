import kivy
kivy.require('1.9.1')

from kivy.cache import Cache
from kivy.utils import platform
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.storage.dictstore import DictStore
from plyer import vibrator

import math
from enum import Enum
from os import listdir
from random import randint
from functools import partial


class TurnAI(object):
    def __init__(self):
        super(TurnAI, self).__init__()
        self.memo = {}


    def is_immeditate_winning_turn_base(self, mat, player_id, dim, row, col, inc_row, inc_col):
        opponent_id = 3 - player_id
        blank_row, blank_col = -1, -1

        for _ in range(dim):
            if mat[row][col] == opponent_id:
                return -1, -1
            elif mat[row][col] == 0:
                if blank_row != -1:     # Multiple blank
                    return (-1, -1)
                blank_row, blank_col = row, col

            row += inc_row
            col += inc_col

        return blank_row, blank_col


    def is_immeditate_winning_turn(self, player_id):
        check_args = Cache.get('my_global_data', 'board_state').check_method_args
        mat = Cache.get('my_global_data', 'board_state').mat
        match_type = Cache.get('my_global_data', 'match_type')
        dim = Cache.get('my_global_data', 'board_dimension')

        for match in match_type:
            blank_row_col = self.is_immeditate_winning_turn_base(mat, player_id, dim, *check_args[match])
            if blank_row_col[0] != -1:
                return blank_row_col

        return -1, -1


    def winning_trend_base(self, board_state, player_id, dim, match_line_end_blocks, row, col, inc_row, inc_col):
        blank_cnt = 0
        opponent_id = 3 - player_id
        blank_row, blank_col = -1, -1

        for _ in range(dim):
            if board_state.mat[row][col] == opponent_id:
                return dim, -1, -1
            if board_state.mat[row][col] == 0:
                blank_cnt += 1
                if blank_cnt == 1:
                    blank_row, blank_col = row, col
                else:
                    if (row, col) in match_line_end_blocks:     # Any end block of match line gets priority.
                        blank_row, blank_col = row, col

            row += inc_row
            col += inc_col

        return blank_cnt, blank_row, blank_col


    def winning_trend(self, player_id):
        board_state = Cache.get('my_global_data', 'board_state')
        check_args = board_state.check_method_args
        match_type = Cache.get('my_global_data', 'match_type')
        dim = Cache.get('my_global_data', 'board_dimension')

        blank_cnt, blank_row, blank_col = dim, -1, -1
        match_type_list = list(match_type)
        match_type_list.remove(match_type.No_match)

        while match_type_list:
                idx = randint(0, len(match_type_list)-1)
                match = match_type_list[idx]
                match_type_list.pop(idx)
                match_line_end_blocks = board_state.match_line_end_blocks(match)

                blank_info = self.winning_trend_base(board_state, player_id, dim, match_line_end_blocks, *check_args[match])

                if blank_info[0] < blank_cnt:
                    row, col = blank_info[1:]
                    r, c, inc_r, inc_c = check_args[match]
                    board_state.mat[row][col] = player_id
                    is_safe = True

                    for _ in range(dim):
                        if board_state.mat[r][c] == 0 and self.is_multiple_attack(3-player_id, r, c):   # (3 - player_id) gives opponent_id
                            is_safe = False
                            break
                        r += inc_r
                        c += inc_c
                    board_state.mat[row][col] = 0

                    if is_safe:
                        blank_cnt, blank_row, blank_col = blank_info

        return blank_cnt, blank_row, blank_col


    def is_multiple_attack(self, player_id, row, col):
        board_state = Cache.get('my_global_data', 'board_state')
        check_args = board_state.check_method_args
        match_type = Cache.get('my_global_data', 'match_type')
        dim = Cache.get('my_global_data', 'board_dimension')

        board_state.mat[row][col] = player_id
        attack_cnt = 0

        for match in match_type:
            if match != match_type.No_match:
                match_line_end_blocks = board_state.match_line_end_blocks(match)

                blank_info = self.winning_trend_base(board_state, player_id, dim, match_line_end_blocks, *check_args[match])
                if blank_info[0] == 1:
                    attack_cnt += 1

        board_state.mat[row][col] = 0
        return attack_cnt > 1


    def start_turn_as_2nd_player(self):
        row, col = -1, -1

        if Cache.get('my_global_data', 'board_state').turn_count == 1 and Cache.get('my_global_data', 'whose_turn') == 2:
            dim = Cache.get('my_global_data', 'board_dimension')
            mat = Cache.get('my_global_data', 'board_state').mat
            mid = dim // 2 + 1

            if mat[mid][mid] == 1:
                row, col = (1, dim)[randint(0, 1)], (1, dim)[randint(0, 1)]     # Any corner of the board.
            elif mat[1][1] or mat[1][dim] or mat[dim][1] or mat[dim][dim]:
                row, col = mid, mid

        return row, col


    def start_first_turn(self):
        row, col = -1, -1

        if Cache.get('my_global_data', 'board_state').turn_count == 0 and Cache.get('my_global_data', 'whose_turn') == 2:
            mat = Cache.get('my_global_data', 'board_state').mat
            dim = Cache.get('my_global_data', 'board_dimension')

            blank_blocks = []
            blank_cnt = 0
            mid = dim // 2 + 1

            for r in range(1, dim + 1):
                for c in range(1, dim + 1):
                    if mat[r][c] == 0:
                        blank_blocks.append((r, c))
                        blank_cnt += 1

            blank_blocks.remove((mid, 1))
            blank_blocks.remove((mid, dim))
            blank_blocks.remove((1, mid))
            blank_blocks.remove((dim, mid))
            blank_cnt -= 4

            row, col = blank_blocks[randint(0, blank_cnt - 1)]

        return row, col


    def any_blank(self):
        mat = Cache.get('my_global_data', 'board_state').mat
        dim = Cache.get('my_global_data', 'board_dimension')

        blank_blocks = []
        blank_cnt = 0

        for r in range(1, dim+1):
            for c in range(1, dim+1):
                if mat[r][c] == 0:
                    blank_blocks.append((r, c))
                    blank_cnt += 1

        return blank_blocks[randint(0, blank_cnt-1)]


    def next_turn(self, player_id):
        board_state = Cache.get('my_global_data', 'board_state')
        mat = board_state.mat
        dim = Cache.get('my_global_data', 'board_dimension')
        game_difficulty = Cache.get('my_global_data', 'game_difficulty')
        opponent_id = 3 - player_id

        print("game_difficulty:", game_difficulty)

        if game_difficulty in (4, ):
            r, c = self.start_first_turn()
            if r != -1:
                print("start_first_turn", r, c)
                return r, c

        if game_difficulty in (1, 2, 3, 4):
            r, c = self.is_immeditate_winning_turn(player_id)
            if r != -1:
                print("is_immediate_winning_turn, player_id", r, c)
                return r, c

        if game_difficulty in (2, 3, 4):
            r, c = self.is_immeditate_winning_turn(opponent_id)
            if r != -1:
                print("is_immediate_winning_turn, opponent_id", r, c)
                return r, c

        if game_difficulty in (3, 4):
            r, c = self.start_turn_as_2nd_player()
            if r != -1:
                print("start_turn_as_2nd_player", r, c)
                return r, c


        if game_difficulty in (2, 4):
            a, b, inc = (1, dim+1, 1) if randint(1, 2) == 1 else (dim, 0, -1)
            for r in range(a, b, inc):
                for c in range(a, b, inc):
                    if mat[r][c] == 0:
                        res = self.is_multiple_attack(player_id, r, c)
                        if res:
                            print("is_multiple_attack, player_id", res)
                            return r, c

        if game_difficulty in (3, 4):
            a, b, inc = (1, dim+1, 1) if randint(1, 2) == 1 else (dim, 0, -1)
            multiple_attack_count = 0
            block = None
            for r in range(a, b, inc):
                for c in range(a, b, inc):
                    if mat[r][c] == 0:
                        res = self.is_multiple_attack(opponent_id, r, c)
                        if res:
                            multiple_attack_count += 1
                            block = r, c

            if multiple_attack_count == 1:      # else go to winning trend.
                print("is_multiple_attack, opponent_id", block)
                return block


        # if game_difficulty in (3, 4):
        #     if mat[dim//2+1][dim//2+1] == 0:
        #         print("mid fill")
        #         return dim//2+1, dim//2+1


        if game_difficulty in (3, 4):
            res = self.winning_trend(player_id)
            if res[0] < dim:
                print("Winning_trend, player_id", res)
                return res[1:]

        if game_difficulty in (4,):
            res = self.winning_trend(opponent_id)
            if res[0] < dim:
                print("Winning_trend, opponent_id", res)
                return res[1:]

        res = self.any_blank()
        print("any_blank", res)
        return res


class PlayerNameTextInput(TextInput):
    def __init__(self, **kwargs):
        super(PlayerNameTextInput, self).__init__(**kwargs)

        self.multiline = False
        self.write_tab = False

        self.text_max_len = 10
        self.bind(text=self.text_bind)
        self.font_name = Cache.get('my_global_data', 'bengali_font_path')


    def text_bind(self, *a):
        mx = self.text_max_len
        if len(self.text) > mx:
            self.text = self.text[:mx]


class RecordManager(object):
    def __init__(self):
        super(RecordManager, self).__init__()

        self.popup_name_input = Popup(title='Wow ! new record', title_color=(0, 1, 1, 1), separator_height=2, title_align='center', size_hint=(0.9, 0.4), auto_dismiss=False)
        self.txt_inp1 = None
        self.txt_inp2 = None
        self.btn_ok = None
        self.is_new_players = True
        self.is_popup_open = False

        self.popup_name_input.bind(on_open=lambda *a: setattr(self, 'is_popup_open', True))
        self.popup_name_input.bind(on_dismiss=lambda *a: setattr(self, 'is_popup_open', False))


    def prompt_player_name(self):
        layout = RelativeLayout()
        layout.add_widget(Image(source='images/popup_background.png', allow_stretch=True, keep_ratio=False, color=(0.5, 0.5, 0.5, 1)))

        if Cache.get('my_global_data', 'player_mood') == 1:
            dialogue = Label(text="Enter player's name (max 10 characters)", bold=True, italic=True, color=(0, 1, 1, 1), size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 0.6})
            self.txt_inp1 = PlayerNameTextInput(text='', hint_text="Enter player's name here", focus=False, size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 1/3})
            self.btn_ok = Button(text='OK', background_color=(0, 0, 0, 0.15), size_hint=(0.5, 0.2), pos_hint={'x': 0.25, 'y': 0})

            layout.add_widget(dialogue)
            layout.add_widget(self.txt_inp1)
            layout.add_widget(self.btn_ok)
        else:
            dialogue1 = Label(text="Enter player-1's name (max 10 characters)", italic=True, color=(0, 1, 1, 1), size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 0.8})
            self.txt_inp1 = PlayerNameTextInput(text='', hint_text="Enter player-1's name here", focus=False, size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 0.6})
            dialogue2 = Label(text="Enter player-2's name (max 10 characters)", italic=True, color=(0, 1, 1, 1), size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 0.4})
            self.txt_inp2 = PlayerNameTextInput(text='', hint_text="Enter player-2's name here", focus=False, size_hint=(1, 0.2), pos_hint={'x': 0, 'y': 0.2})
            self.btn_ok = Button(text='OK', color=(0, 1, 1, 1), background_color=(0, 0, 0, 0.3), size_hint=(0.5, 0.2), pos_hint={'x': 0.25, 'y': 0})

            layout.add_widget(dialogue1)
            layout.add_widget(self.txt_inp1)
            layout.add_widget(dialogue2)
            layout.add_widget(self.txt_inp2)
            layout.add_widget(self.btn_ok)

        self.btn_ok.bind(on_release=self.btn_ok_do)
        self.popup_name_input.content = layout
        self.popup_name_input.open()
        Clock.schedule_once(lambda *a: setattr(self.txt_inp1, 'focus', True), 0.2)


    def btn_ok_do(self, *a):
        store = Cache.get('my_global_data', 'records_store')
        is_empty_field = False

        if Cache.get('my_global_data', 'player_mood') == 1:
            if self.txt_inp1.text:
                player_score = int(Cache.get('my_global_data', 'game_layout_topbox').label_player1_score.text)
                cpu_score = int(Cache.get('my_global_data', 'game_layout_topbox').label_player2_score.text)
                player_name = self.txt_inp1.text

                rec_scr_layout = Cache.get('my_global_data', 'records_screen_layout')
                diffi = ('easy', 'medium', 'hard', 'intense')[Cache.get('my_global_data', 'game_difficulty')-1]

                store.put(diffi, player_score=player_score, cpu_score=cpu_score, player_name=player_name)
                setattr(getattr(rec_scr_layout, 'label_' + diffi + '_player_score'), 'text', str(player_score))
                setattr(getattr(rec_scr_layout, 'label_' + diffi + '_cpu_score'), 'text', str(cpu_score))
                setattr(getattr(rec_scr_layout, 'label_' + diffi + '_player_name'), 'text', player_name)
            else:
                is_empty_field = True
        else:
            if self.txt_inp1.text and self.txt_inp2.text:
                player1_score = int(Cache.get('my_global_data', 'game_layout_topbox').label_player1_score.text)
                player2_score = int(Cache.get('my_global_data', 'game_layout_topbox').label_player2_score.text)
                player1_name = self.txt_inp1.text
                player2_name = self.txt_inp2.text

                rec_scr_layout = Cache.get('my_global_data', 'records_screen_layout')

                store.put('dual', player1_score=player1_score, player2_score=player2_score, player1_name=player1_name, player2_name=player2_name)
                setattr(getattr(rec_scr_layout, 'label_dual_player1_score'), 'text', str(player1_score))
                setattr(getattr(rec_scr_layout, 'label_dual_player2_score'), 'text', str(player2_score))
                setattr(getattr(rec_scr_layout, 'label_dual_player1_name'), 'text', player1_name)
                setattr(getattr(rec_scr_layout, 'label_dual_player2_name'), 'text', player2_name)
            else:
                is_empty_field = True

        if not is_empty_field:
            self.popup_name_input.dismiss()


class GameManager(object):
    def __init__(self):
        super(GameManager, self).__init__()

        self.board_state_ref = Cache.get('my_global_data', 'board_state')
        self.match_type = Cache.get('my_global_data', 'match_type')
        self.turn_ai = TurnAI()


    def got_turn_on(self, row, col):
        who = Cache.get('my_global_data', 'whose_turn')
        self.board_state_ref.turn_on(row, col, who)

        match = self.board_state_ref.check_any_match()

        if match == self.match_type.No_match:
            dim = Cache.get('my_global_data', 'board_dimension')

            if self.board_state_ref.turn_count == dim * dim:
                game_screen_layout = Cache.get('my_global_data', 'game_screen_layout')
                game_screen_layout.show_popup_draw()
            else:
                who = 3 - who
                Cache.append('my_global_data', 'whose_turn', who)
                topbox = Cache.get('my_global_data', 'game_layout_topbox')
                topbox.show_dialogue("Player-%d's turn" % (who))

                if Cache.get('my_global_data', 'player_mood') == 1 and who == 2:
                    r, c = self.turn_ai.next_turn(2)
                    Cache.get('my_global_data', 'game_layout_board_wrapper').board.turn_buttons[dim * (r-1) + c].perform_turn()
                return
        else:
            Cache.append('my_global_data', 'player_winner', who)
            board_wrapper = Cache.get('my_global_data', 'game_layout_board_wrapper')
            game_screen_layout = Cache.get('my_global_data', 'game_screen_layout')

            board_wrapper.draw_match_line(match)
            if who == 1:
                game_screen_layout.topbox.label_player1_score.text = str(int(game_screen_layout.topbox.label_player1_score.text) + 1)
            else:
                game_screen_layout.topbox.label_player2_score.text = str(int(game_screen_layout.topbox.label_player2_score.text) + 1)

            Clock.schedule_once(game_screen_layout.show_popup_winner, 0.60)

        self.board_state_ref.reset_matrix()
        Cache.append('my_global_data', 'whose_turn', 0)


class BoardState(object):
    def __init__(self):
        super(BoardState, self).__init__()

        dim = Cache.get('my_global_data', 'board_dimension')
        match_type = Cache.get('my_global_data', 'match_type')

        self.turn_count = 0
        self.mat = [[0] * (dim + 1) for x in range(dim + 1)]
        self.check_method_args = {match_type.H_top: (1, 1, 0, 1),
                                  match_type.H_mid: (dim//2+1, 1, 0, 1),
                                  match_type.H_bottom: (dim, 1, 0, 1),
                                  match_type.V_left: (1, 1, 1, 0),
                                  match_type.V_mid: (1, dim//2+1, 1, 0),
                                  match_type.V_right: (1, dim, 1, 0),
                                  match_type.D_tl_br: (1, 1, 1, 1),
                                  match_type.D_tr_bl: (1, dim, 1, -1),
                                  match_type.No_match: (1, 1, 0, 0)}


    def update_check_method_args(self):
        dim = Cache.get('my_global_data', 'board_dimension')
        match_type = Cache.get('my_global_data', 'match_type')

        self.check_method_args = {match_type.H_top: (1, 1, 0, 1),
                                  match_type.H_mid: (dim // 2 + 1, 1, 0, 1),
                                  match_type.H_bottom: (dim, 1, 0, 1),
                                  match_type.V_left: (1, 1, 1, 0),
                                  match_type.V_mid: (1, dim // 2 + 1, 1, 0),
                                  match_type.V_right: (1, dim, 1, 0),
                                  match_type.D_tl_br: (1, 1, 1, 1),
                                  match_type.D_tr_bl: (1, dim, 1, -1),
                                  match_type.No_match: (1, 1, 0, 0)}


    def match_line_end_blocks(self, match):
        dim = Cache.get('my_global_data', 'board_dimension')
        r, c, inc_r, inc_c = self.check_method_args[match]
        return (r, c), (r + inc_r * (dim - 1), c + inc_c * (dim - 1))


    def check_base(self, dim, row, col, inc_row, inc_col):
        val = self.mat[row][col]

        if val == 0:
            return False

        for _ in range(dim):
            if self.mat[row][col] != val:
                return False
            row += inc_row
            col += inc_col

        return True


    def check_any_match(self):
        dim = Cache.get('my_global_data', 'board_dimension')
        match_type = Cache.get('my_global_data', 'match_type')

        for mt in match_type:
            if self.check_base(dim, *self.check_method_args[mt]):
                return mt

        return match_type.No_match


    def reset_matrix(self, *a):
        dim = Cache.get('my_global_data', 'board_dimension')
        if dim != len(self.mat):
            self.update_check_method_args()
        self.mat = [[0] * (dim + 1) for _ in range(dim + 1)]
        self.turn_count = 0


    def turn_on(self, row, col, player_id):
        self.mat[row][col] = player_id
        self.turn_count += 1


# UI parts *********************************************************************


class TurnButton(Button):
    def __init__(self, **kwargs):
        super(TurnButton, self).__init__(**kwargs)

        self.is_turned = False
        self.bind(on_release=self.perform_turn)


    def perform_turn(self, *a):
        if not self.is_turned:
            who = Cache.get('my_global_data', 'whose_turn')
            if who != 0:
                self.is_turned = True
                self.background_normal = "images/player_icons/" + Cache.get('my_global_data', 'player%d_icon_name' % (who))

                game_manager = Cache.get('my_global_data', 'game_manager')
                row, col = self.id.split()
                row, col = int(row), int(col)
                game_manager.got_turn_on(row, col)


    def reset_turn(self, *a):
        self.is_turned = False;
        self.background_normal = "images/blank_button.png"


class BoardBackLayout(GridLayout):
    def __init__(self, **kwargs):
        super(BoardBackLayout, self).__init__(**kwargs)

        dim = Cache.get('my_global_data', 'board_dimension')
        self.padding = 5
        self.spacing = 5
        self.cols = dim

        for i in range(1, dim*dim+1):
            self.add_widget(Image(source='images/board_button_background.png', allow_stretch=True, keep_ratio=False))


    def reform_now(self, *a):
        dim = Cache.get('my_global_data', 'board_dimension')
        self.clear_widgets()
        self.cols = dim

        for i in range(1, dim*dim+1):
            self.add_widget(Image(source='images/board_button_background.png', allow_stretch=True, keep_ratio=False))


class BoardLayout(GridLayout):
    def __init__(self, **kwargs):
        super(BoardLayout, self).__init__(**kwargs)

        dim = Cache.get('my_global_data', 'board_dimension')

        self.padding = 5
        self.spacing = 5
        self.cols = dim
        self.turn_buttons = [None] * (dim*dim+1)
        self.match_line = None
        self.match_line_anim = None

        for i in range(1, dim+1):
            for j in range(1, dim+1):
                self.turn_buttons[(i-1)*dim+j] = TurnButton(id='%d %d' % (i, j), background_normal='images/blank_button.png')
                self.add_widget(self.turn_buttons[(i-1)*dim+j])


    def reset_now(self, *a):
        Cache.get('my_global_data', 'board_state').reset_matrix()
        dim = Cache.get('my_global_data', 'board_dimension')

        for i in range(1, dim*dim+1):
            self.turn_buttons[i].reset_turn()


    def reform_now(self, *a):
        dim = Cache.get('my_global_data', 'board_dimension')
        self.clear_widgets()
        self.cols = dim
        self.turn_buttons = [None] * (dim * dim + 1)

        for i in range(1, dim + 1):
            for j in range(1, dim + 1):
                self.turn_buttons[(i - 1) * dim + j] = TurnButton(id="%d %d" % (i, j), background_normal='images/blank_button.png')
                self.add_widget(self.turn_buttons[(i - 1) * dim + j])


    def draw_match_line(self, match):
        dim = Cache.get('my_global_data', 'board_dimension')
        match_type = Cache.get('my_global_data', 'match_type')
        tb = self.turn_buttons
        delta = tb[1].size[0] / 3

        if match == match_type.H_top:
            x1, y1, x2, y2 = tb[1].center + tb[dim].center
            x1 -= delta
            x2 += delta
        elif match == match_type.H_mid:
            x1, y1, x2, y2 = tb[(dim // 2) * dim + 1].center + tb[(dim // 2 + 1) * dim].center
            x1 -= delta
            x2 += delta
        elif match == match_type.H_bottom:
            x1, y1, x2, y2 = tb[dim * (dim - 1) + 1].center + tb[dim * dim].center
            x1 -= delta
            x2 += delta
        elif match == match_type.V_left:
            x1, y1, x2, y2 = tb[1].center + tb[dim * (dim - 1) + 1].center
            y1 += delta
            y2 -= delta
        elif match == match_type.V_mid:
            x1, y1, x2, y2 = tb[dim // 2 + 1].center + tb[dim * dim - dim // 2].center
            y1 += delta
            y2 -= delta
        elif match == match_type.V_right:
            x1, y1, x2, y2 = tb[dim].center + tb[dim * dim].center
            y1 += delta
            y2 -= delta
        elif match == match_type.D_tl_br:
            x1, y1, x2, y2 = tb[1].center + tb[dim * dim].center
            x1 -= delta
            y1 += delta
            x2 += delta
            y2 -= delta
        elif match == match_type.D_tr_bl:
            x1, y1, x2, y2 = tb[dim].center + tb[dim * (dim - 1) + 1].center
            x1 += delta
            y1 += delta
            x2 -= delta
            y2 -= delta
        else:
            return

        with self.canvas:
            Color(0, 1, 1, 1)
            self.match_line = Line(points=[x1, y1, x1, y1], width=7)
        self.canvas.remove(self.match_line)

        self.match_line_anim = Animation(points=(x1, y1, x2, y2), d=0.30)
        self.match_line_anim.bind(on_complete =lambda *a: Clock.schedule_once(self.remove_match_line, 0.30))

        self.canvas.add(self.match_line)
        self.match_line_anim.start(self.match_line)


    def remove_match_line(self, *a):
        self.canvas.remove(self.match_line)


class TopboxLayout(RelativeLayout):
    def __init__(self, **kwargs):
        super(TopboxLayout, self).__init__(**kwargs)

        self.back_btn = Button(text='Home', italic=True, bold=True, color=(0, 1, 1, 1), background_color=(0, 0, 0, 0), size_hint=(0.2, 0.5), pos_hint={'x': 0, 'y': 0.5}, on_press=self.go_home)
        self.reset_btn = Button(text='Reset', italic=True, bold=True, color=(0, 1, 1, 1), background_color=(0, 0, 0, 0), size_hint=(0.2, 0.5), pos_hint={'x': 0.8, 'y': 0.5}, on_press=self.reset_now)
        self.dialogue_label = Label(text="Player-1 turns first\nor to select\npress on player's icon.", bold=False, italic=True, color=(1, 1, 1, 1), halign='center', size_hint=(0.6, 0.5), pos_hint={'x': 0.2, 'y': 0.5})
        self.player1_btn = Button(background_normal='images/player_icons/'+Cache.get('my_global_data', 'player1_icon_name'), on_release=self.player1_btn_pressed, size_hint=(0.25, 0.5), pos_hint={'x': 0, 'y': 0})
        self.player2_btn = Button(background_normal='images/player_icons/' + Cache.get('my_global_data', 'player2_icon_name'), on_release=self.player2_btn_pressed, size_hint=(0.25, 0.5), pos_hint={'x': 0.75, 'y': 0})
        self.label_player1_score = Label(text='0', bold=True, italic=True, color=(1, 1, 0, 1), size_hint=(0.25, 0.5), pos_hint={'x': 0.25, 'y': 0})
        self.label_player2_score = Label(text='0', bold=True, italic=True, color=(1, 1, 0, 1), size_hint=(0.25, 0.5), pos_hint={'x': 0.5, 'y': 0})
        self.max_score_by_new_player = False

        self.label_player1_score.bind(text=self.score_bind)
        self.label_player2_score.bind(text=self.score_bind)

        self.add_widget(self.back_btn)
        self.add_widget(self.reset_btn)
        self.add_widget(self.dialogue_label)
        self.add_widget(self.player1_btn)
        self.add_widget(self.player2_btn)
        self.add_widget(self.label_player1_score)
        self.add_widget(self.label_player2_score)
        self.add_widget(Label(text='VS', bold=True, italic=False, color=(0.75, 1, 0, 1), size_hint=(0.01, 0.5), pos_hint={'x': 0.5, 'y': 0}))


    def score_bind(self, *a):
        rec_man = Cache.get('my_global_data', 'record_manager')
        store = Cache.get('my_global_data', 'records_store')
        player_mood = Cache.get('my_global_data', 'player_mood')

        p1, p2 = int(self.label_player1_score.text), int(self.label_player2_score.text)
        mx = max(p1, p2)
        is_max_score = False

        if player_mood == 1:
            diffi = ('easy', 'medium', 'hard', 'intense')[Cache.get('my_global_data', 'game_difficulty') - 1]
            store_p1, store_p2 = store.get(diffi)['player_score'], store.get(diffi)['cpu_score']
        else:
            store_p1, store_p2 = store.get('dual')['player1_score'], store.get('dual')['player2_score']

        store_mx = max(store_p1, store_p2)

        if mx > store_mx:
            is_max_score = True
        elif mx == store_mx:
            if p1 + p2 > store_p1 + store_p2:
                is_max_score = True

        if is_max_score:
            if rec_man.is_new_players:
                rec_man.is_new_players = False
                self.max_score_by_new_player = True     # it'll be used in GameScreenLayout.after_popup_winner().
            else:
                rec_man.btn_ok_do()


    def player1_btn_pressed(self, *a):
        if Cache.get('my_global_data', 'board_state').turn_count == 0:
            Cache.append('my_global_data', 'whose_turn', 1)


    def player2_btn_pressed(self, *a):
        if Cache.get('my_global_data', 'board_state').turn_count == 0:
            Cache.append('my_global_data', 'whose_turn', 2)

            if Cache.get('my_global_data', 'player_mood') == 1:
                r, c = Cache.get('my_global_data', 'game_manager').turn_ai.next_turn(2)
                dim = Cache.get('my_global_data', 'board_dimension')
                Cache.get('my_global_data', 'game_layout_board_wrapper').board.turn_buttons[dim * (r - 1) + c].perform_turn()


    def go_home(self, *a):
        self.parent.go_home()


    def show_dialogue(self, dialogue):
        self.dialogue_label.text = dialogue


    def reset(self, *a):
        self.label_player1_score.text = '0'
        self.label_player2_score.text = '0'
        self.dialogue_label.text = "Player-1 turns first\nor to select\npress on player's icon."


    def reset_now(self, *a):
        self.parent.reset_now()
        self.reset()
        Cache.get('my_global_data', 'record_manager').is_new_players = True


class BoardWrapperLayout(RelativeLayout):
    def __init__(self, **kwargs):
        super(BoardWrapperLayout, self).__init__(**kwargs)

        self.board_back = BoardBackLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.board = BoardLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        self.add_widget(self.board_back)
        self.add_widget(self.board)


    def reset_now(self, *a):
        self.board.reset_now()


    def reform_now(self, *a):
        self.board.reform_now()
        self.board_back.reform_now()
        Cache.get('my_global_data', 'board_state').reset_matrix()


    def draw_match_line(self, match):
        self.board.draw_match_line(match)


class BottomboxLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(BottomboxLayout, self).__init__(**kwargs)

        self.label_mode = Label(text='[i][b]Player mode:[/b]  Single (with CPU)\n[b]Difficulty:[/b]  Medium[/i]', markup=True, halign='center', color=(1, 1, 0.75, 1), size_hint=(1, 0.5), pos_hint={'x': 0, 'y': 0.5})
        self.add_widget(self.label_mode)


    def set_label_mode(self, *a):
        if Cache.get('my_global_data', 'player_mood') == 1:
            self.label_mode.text = '[i][b]Player mode:[/b]  Single (with CPU)\n[b]Difficulty:[/b]  ' + ('Easy', 'Medium', 'Hard', 'Intense')[Cache.get('my_global_data', 'game_difficulty')-1] + '[/i]'
        else:
            self.label_mode.text = self.label_mode.text = '[i][b]Player mode:[/b]  Dual[/i]'


class GameScreenLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(GameScreenLayout, self).__init__(**kwargs)

        back_img = Image(source='images/game_screen_background.png', allow_stretch=True, keep_ratio=False, color=(1, 1, 1, 0.75))
        self.add_widget(back_img)

        board_h = Window.width
        box_h = (Window.height - Window.width) / 2

        board_h = board_h / Window.height     # convert in percent
        box_h = box_h / Window.height

        self.board = BoardWrapperLayout(size_hint=(1.0, board_h), pos_hint={'x': 0, 'y': box_h})
        self.topbox = TopboxLayout(size_hint=(1, box_h), pos_hint={'x': 0, 'y': box_h+board_h})
        self.bottombox = BottomboxLayout(size_hint=(1, box_h), pos_hint={'x': 0, 'y': 0})

        self.add_widget(self.board)
        self.add_widget(self.topbox)
        self.add_widget(self.bottombox)

        self.popup_winner = Popup(title='Game over', title_color=(0, 1, 1, 1), separator_height=0, title_align='center', size_hint=(0.9, 0.4))
        self.popup_winner_player_icon = Image()     # image source will be added in self.show_popup_winner()
        self.popup_winner_image = Image()           # image source will be added in self.show_popup_winner()
        layout = RelativeLayout()
        layout.add_widget(Image(source='images/popup_background.png', allow_stretch=True, keep_ratio=False))
        layout.add_widget(self.popup_winner_player_icon)
        layout.add_widget(self.popup_winner_image)
        self.popup_winner.content = layout
        self.popup_winner.bind(on_touch_down=self.popup_winner.dismiss)
        self.popup_winner.bind(on_dismiss=self.after_popup_winner)

        self.popup_draw = Popup(title='Game over', title_color=(0, 1, 1, 1), separator_height=0, title_align='center', size_hint=(0.9, 0.4))
        self.popup_draw_player1_icon = Image(allow_stretch=True, keep_ratio=False, size_hint=(0.5, 1), pos_hint={'x': 0, 'y': 0})     # image source will be added in self.show_popup_winner()
        self.popup_draw_player2_icon = Image(allow_stretch=True, keep_ratio=False, size_hint=(0.5, 1), pos_hint={'x': 0.5, 'y': 0})     # image source will be added in self.show_popup_winner()
        self.popup_draw_image = Image()                 # image source will be added in self.show_popup_winner()
        layout = RelativeLayout()
        layout.add_widget(Image(source='images/popup_background.png', allow_stretch=True, keep_ratio=False))
        layout.add_widget(self.popup_draw_player1_icon)
        layout.add_widget(self.popup_draw_player2_icon)
        layout.add_widget(self.popup_draw_image)
        self.popup_draw.content = layout
        self.popup_draw.bind(on_touch_down=self.popup_draw.dismiss)
        self.popup_draw.bind(on_dismiss=self.after_popup_draw)

        self.sound = None

        Cache.append('my_global_data', 'game_layout_topbox', self.topbox)
        Cache.append('my_global_data', 'game_layout_board_wrapper', self.board)
        Cache.append('my_global_data', 'game_layout_bottombox', self.bottombox)


    def go_home(self, *a):
        Cache.get('my_global_data', 'play_button_press_sound')()
        self.parent.manager.transition.direction = 'right'
        self.parent.manager.current = 'home_screen'


    def reset_now(self, *a):
        Cache.get('my_global_data', 'play_button_press_sound')()
        self.board.reset_now()


    def show_popup_winner(self, *a):
        if Cache.get('my_global_data', 'sound_state'):
            sound = Cache.get('my_global_data', 'popup_winner_sound')
            if sound:
                sound.play()
                self.sound = sound

        Cache.get('my_global_data', 'vibrate_after_checking')()

        self.popup_winner_player_icon.source = 'images/player_icons/' + Cache.get('my_global_data', 'player%d_icon_name' % (Cache.get('my_global_data', 'player_winner')))
        self.popup_winner_image.source = 'images/popup_winner_image_%d.png' % (randint(1, 2))

        anim = Animation(size_hint=(0.9, 0.4), d=0.4)
        self.popup_winner.size_hint = (0.1, 0.1)
        self.popup_winner.open()
        anim.start(self.popup_winner)


    def after_popup_winner(self, *a):
        sound = self.sound
        if sound and sound.state == 'play':
            sound.stop()

        self.board.reset_now()
        Cache.append('my_global_data', 'player_winner', 0)
        Cache.append('my_global_data', 'whose_turn', 1)
        self.topbox.dialogue_label.text = "Player-1 turns first\nor to select\npress on player's icon."

        topbox = Cache.get('my_global_data', 'game_layout_topbox')

        if topbox.max_score_by_new_player:
            topbox.max_score_by_new_player = False
            Cache.get('my_global_data', 'record_manager').prompt_player_name()


    def show_popup_draw(self, *a):
        if Cache.get('my_global_data', 'sound_state'):
            sound = Cache.get('my_global_data', 'popup_draw_sound')
            if sound:
                sound.play()
                self.sound = sound

        Cache.get('my_global_data', 'vibrate_after_checking')()

        self.popup_draw_player1_icon.source = 'images/player_icons/' + Cache.get('my_global_data', 'player1_icon_name')
        self.popup_draw_player2_icon.source = 'images/player_icons/' + Cache.get('my_global_data', 'player2_icon_name')
        self.popup_draw_image.source = 'images/popup_draw_image.png'

        anim = Animation(size_hint=(0.9, 0.4), d=0.4)
        self.popup_draw.size_hint = (0.1, 0.1)
        self.popup_draw.open()
        anim.start(self.popup_draw)


    def after_popup_draw(self, *a):
        sound = self.sound
        if sound and sound.state == 'play':
            sound.stop()

        self.board.reset_now()
        Cache.append('my_global_data', 'player_winner', 0)
        Cache.append('my_global_data', 'whose_turn', 1)
        self.topbox.dialogue_label.text = "Player-1 turns first\nor to select\npress on player's icon."


class CustomSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super(CustomSpinnerOption, self).__init__(**kwargs)
        self.color = (0, 1, 1, 1)
        # self.font_size = 20
        self.background_normal = 'images/blank_button.png'


class CustomToggleButton(ToggleButton):
    def __init__(self, **kwargs):
        super(CustomToggleButton, self).__init__(**kwargs)

        self.background_normal = "images/blank_button.png"
        self.background_down = "images/tick_mark.png"
        self.bind(on_press=self.on_press_do)

    def on_press_do(self, *a):
        self.state = 'down'


class SettingsScreenLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(SettingsScreenLayout, self).__init__(**kwargs)

        self.back_btn = Button(text='Save', on_release=self.go_to_home_screen, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*7})
        self.set_default_btn = Button(text='Set Default', on_release=self.set_default, size_hint=(0.5, 1/8), pos_hint={'x': 0.5, 'y': 1/8*7})
        self.board_dimension_label = Label(text='Dimension :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*6})
        self.board_dimension_spinner = Spinner(text='3', values=('3', '5'), option_cls=CustomSpinnerOption, size_hint=(0.075, 0.075), pos_hint={'center_x': 0.75, 'center_y': 1/8*6.5})
        self.sound_label = Label(text='Sound :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*5})
        self.sound_switch = Switch(active=True, size_hint=(0.5, 1/8), pos_hint={'x': 0.5, 'y': 1/8*5})
        self.vibration_label = Label(text='Vibration :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*4})
        self.vibration_switch = Switch(active=True, size_hint=(0.5, 1/8), pos_hint={'x': 0.5, 'y': 1/8*4})
        self.player_mode_label = Label(text='Player mode :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*3})
        self.player_mode_single_toggle_btn = CustomToggleButton(text='Single', group='player_mode', state='down', size_hint=(0.25, 1/8), pos_hint={'x': 0.5, 'y': 1/8*3})
        self.player_mode_dual_toggle_btn = CustomToggleButton(text='Dual', group='player_mode', size_hint=(0.25, 1/8), pos_hint={'x': 0.75, 'y': 1/8*3})
        self.difficulty_label = Label(text='Difficulty :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8*2})
        self.difficulty_spinner = Spinner(text='Medium', values=('Easy', 'Medium', 'Hard', 'Intense'), option_cls=CustomSpinnerOption, size_hint=(0.35, 0.035), pos_hint={'center_x': 0.75, 'center_y': 1/8*2.5})
        self.player_icon_label = Label(text='Select player icon :', bold=False, italic=True, size_hint=(0.5, 1/8), pos_hint={'x': 0, 'y': 1/8})

        player1_icon_dropdown = DropDown()
        player1_icon_dropdown_main_btn = Button(background_normal="images/player_icons/" + Cache.get('my_global_data', 'player1_icon_name'), size_hint=(0.25, 1/8), pos_hint={'x': 0.5, 'y': 1/8})
        player1_icon_dropdown_main_btn.bind(on_release=player1_icon_dropdown.open)
        player1_icon_dropdown_main_btn.bind(on_release=self.refresh_player1_icon_dropdown_list)
        player1_icon_dropdown.bind(on_select=lambda instance, x: setattr(player1_icon_dropdown_main_btn, 'background_normal', x))

        player2_icon_dropdown = DropDown()
        player2_icon_dropdown_main_btn = Button(background_normal="images/player_icons/" + Cache.get('my_global_data', 'player2_icon_name'), size_hint=(0.25, 1/8), pos_hint={'x': 0.75, 'y': 1/8})
        player2_icon_dropdown_main_btn.bind(on_release=player2_icon_dropdown.open)
        player2_icon_dropdown_main_btn.bind(on_release=self.refresh_player2_icon_dropdown_list)
        player2_icon_dropdown.bind(on_select=lambda instance, x: setattr(player2_icon_dropdown_main_btn, 'background_normal', x))

        self.player1_icon_dropdown = player1_icon_dropdown
        self.player2_icon_dropdown = player2_icon_dropdown

        self.player1_icon_dropdown_main_btn = player1_icon_dropdown_main_btn
        self.player2_icon_dropdown_main_btn = player2_icon_dropdown_main_btn

        self.player_mode_single_toggle_btn.bind(state=self.difficulty_dependence_on_player_mode)

        self.add_widget(self.back_btn)
        self.add_widget(self.set_default_btn)
        self.add_widget(self.board_dimension_label)
        self.add_widget(self.board_dimension_spinner)
        self.add_widget(self.sound_label)
        self.add_widget(self.sound_switch)
        self.add_widget(self.vibration_label)
        self.add_widget(self.vibration_switch)
        self.add_widget(self.player_mode_label)
        self.add_widget(self.player_mode_single_toggle_btn)
        self.add_widget(self.player_mode_dual_toggle_btn)
        self.add_widget(self.difficulty_label)
        self.add_widget(self.difficulty_spinner)
        self.add_widget(self.player_icon_label)
        self.add_widget(self.player1_icon_dropdown_main_btn)
        self.add_widget(self.player2_icon_dropdown_main_btn)


    def set_default(self, *a):
        Cache.get('my_global_data', 'play_button_press_sound')()

        self.board_dimension_spinner.text = '3'
        self.sound_switch.active = True
        self.vibration_switch.active = True
        self.player_mode_single_toggle_btn.state = 'down'
        self.difficulty_spinner.text = 'Medium'
        self.player1_icon_dropdown_main_btn.background_normal = "images/player_icons/player_icon_1.png"
        self.player2_icon_dropdown_main_btn.background_normal = "images/player_icons/player_icon_2.png"


    def go_to_home_screen(self, *a):
        if self.sound_switch.active != Cache.get('my_global_data', 'sound_state'):
            Cache.append('my_global_data', 'sound_state', self.sound_switch.active)

        if self.vibration_switch.active != Cache.get('my_global_data', 'vibration_state'):
            Cache.append('my_global_data', 'vibration_state', self.vibration_switch.active)

        Cache.get('my_global_data', 'play_button_press_sound')()

        dim = Cache.get('my_global_data', 'board_dimension')
        is_dim_changed = False
        is_player1_icon_changed = False
        is_player2_icon_changed = False
        is_player_mood_changed = False
        is_difficulty_changed = False

        difficulty_spinner_text = self.difficulty_spinner.text
        game_difficulty = Cache.get('my_global_data', 'game_difficulty')

        if difficulty_spinner_text == 'Easy' and game_difficulty != 1:
            Cache.append('my_global_data', 'game_difficulty', 1)
            is_difficulty_changed = True
        elif difficulty_spinner_text == 'Medium' and game_difficulty != 2:
            Cache.append('my_global_data', 'game_difficulty', 2)
            is_difficulty_changed = True
        elif difficulty_spinner_text == 'Hard' and game_difficulty != 3:
            Cache.append('my_global_data', 'game_difficulty', 3)
            is_difficulty_changed = True
        elif difficulty_spinner_text == 'Intense' and game_difficulty != 4:
            Cache.append('my_global_data', 'game_difficulty', 4)
            is_difficulty_changed = True

        if is_difficulty_changed:
            Cache.get('my_global_data', 'board_state').reset_matrix()
            Cache.get('my_global_data', 'game_layout_board_wrapper').reform_now()
            Cache.get('my_global_data', 'game_layout_topbox').reset()
            Cache.get('my_global_data', 'record_manager').is_new_players = True

        player_mood = Cache.get('my_global_data', 'player_mood')

        if player_mood == 1 and self.player_mode_single_toggle_btn.state != 'down':
            Cache.append('my_global_data', 'player_mood', 2)
            is_player_mood_changed = True
        elif player_mood == 2 and self.player_mode_dual_toggle_btn.state != 'down':
            Cache.append('my_global_data', 'player_mood', 1)
            is_player_mood_changed = True

        if is_player_mood_changed:
            Cache.get('my_global_data', 'record_manager').is_new_players = True

        if int(self.board_dimension_spinner.text) != dim or is_player_mood_changed:
            is_dim_changed = True
            dim = int(self.board_dimension_spinner.text)
            Cache.append('my_global_data', 'board_dimension', dim)
            Cache.get('my_global_data', 'board_state').reset_matrix()
            Cache.get('my_global_data', 'game_layout_topbox').reset()
            Cache.get('my_global_data', 'game_layout_board_wrapper').reform_now()
            Cache.append('my_global_data', 'whose_turn', 1)

        if Cache.get('my_global_data', 'player1_icon_name') != self.player1_icon_dropdown_main_btn.background_normal[20:]:
            is_player1_icon_changed = True
            Cache.append('my_global_data', 'player1_icon_name', self.player1_icon_dropdown_main_btn.background_normal[20:])
            Cache.get('my_global_data', 'game_layout_topbox').player1_btn.background_normal = self.player1_icon_dropdown_main_btn.background_normal

        if Cache.get('my_global_data', 'player2_icon_name') != self.player2_icon_dropdown_main_btn.background_normal[20:]:
            is_player2_icon_changed = True
            Cache.append('my_global_data', 'player2_icon_name', self.player2_icon_dropdown_main_btn.background_normal[20:])
            Cache.get('my_global_data', 'game_layout_topbox').player2_btn.background_normal = self.player2_icon_dropdown_main_btn.background_normal

        if is_dim_changed == False and (is_player1_icon_changed or is_player2_icon_changed):
                mat = Cache.get('my_global_data', 'board_state').mat
                turn_buttons = Cache.get('my_global_data', 'game_layout_board_wrapper').board.turn_buttons
                img1 = "images/player_icons/" + Cache.get('my_global_data', 'player1_icon_name')
                img2 = "images/player_icons/" + Cache.get('my_global_data', 'player2_icon_name')

                for i in range(1, dim+1):
                    for j in range(1, dim+1):
                        if mat[i][j] == 1 and is_player1_icon_changed:
                            turn_buttons[(i - 1) * dim + j].background_normal = img1
                        elif mat[i][j] == 2 and is_player2_icon_changed:
                            turn_buttons[(i - 1) * dim + j].background_normal = img2

        if self.sound_switch.active != Cache.get('my_global_data', 'sound_state'):
            Cache.append('my_global_data', 'sound_state', self.sound_switch.active)

        Cache.get('my_global_data', 'game_layout_bottombox').set_label_mode()

        self.parent.parent.transition.direction = 'right'
        self.parent.parent.current = 'home_screen'


    def refresh_player1_icon_dropdown_list(self, *a):
        L = Cache.get('my_global_data', 'player_icon_list')[0:]     # Copy of the list
        L.remove(self.player2_icon_dropdown_main_btn.background_normal[20:])
        player1_icon_dropdown = self.player1_icon_dropdown

        player1_icon_dropdown.clear_widgets()

        for icon_name in L:
            btn = Button(background_normal="images/player_icons/" + icon_name, size_hint_y=None)
            btn.height = btn.width
            btn.bind(on_release=lambda btn: player1_icon_dropdown.select(btn.background_normal))
            player1_icon_dropdown.add_widget(btn)


    def refresh_player2_icon_dropdown_list(self, *a):
        L = Cache.get('my_global_data', 'player_icon_list')[0:]     # Copy of the list
        L.remove(self.player1_icon_dropdown_main_btn.background_normal[20:])
        player2_icon_dropdown = self.player2_icon_dropdown

        player2_icon_dropdown.clear_widgets()

        for icon_name in L:
            btn = Button(background_normal="images/player_icons/" + icon_name, size_hint_y=None)
            btn.height = btn.width
            btn.bind(on_release=lambda btn: player2_icon_dropdown.select(btn.background_normal))
            player2_icon_dropdown.add_widget(btn)


    def difficulty_dependence_on_player_mode(self, *a):
        val = 1.0 if self.player_mode_single_toggle_btn.state == 'down' else 0.5
        self.difficulty_label.opacity = val
        self.difficulty_spinner.opacity = val


class Menu(RelativeLayout):
    def __init__(self, **kwargs):
        super(Menu, self).__init__(**kwargs)

        self.start_angle = None         # These attributes will be assigned in pass_info() method.
        self.menu_list_radius_hint = None
        self.total_duration = None
        self.menu_list = None

        self.btn_menu = None
        self.menu_list_btns = []
        self.connect_lines = []
        self.is_menu_open = False
        self.is_menu_list_callback_called = False
        self.trans = ('in_back', 'in_bounce', 'in_circ', 'in_cubic', 'in_elastic', 'in_expo', 'in_out_back', 'in_out_bounce', 'in_out_circ', 'in_out_cubic', 'in_out_elastic', 'in_out_expo', 'in_out_quad', 'in_out_quart', 'in_out_quint', 'in_out_sine', 'in_quad', 'in_quart', 'in_quint', 'in_sine', 'linear', 'out_back', 'out_bounce', 'out_circ', 'out_cubic', 'out_elastic', 'out_expo', 'out_quad', 'out_quart', 'out_quint', 'out_sine')


    def set_attributes(self, *, start_angle, menu_list_radius_hint, line_start_away_hint, total_duration, menu_list):
        self.start_angle = start_angle
        self.menu_list_radius_hint = menu_list_radius_hint
        self.line_start_away_hint = line_start_away_hint
        self.total_duration = total_duration
        self.menu_list = menu_list

        for btn_text, call_back in self.menu_list:
            btn = Button(text=btn_text, italic=True, bold=True, color=(0, 1, 1, 1), background_color=(0, 0, 0, 0), opacity=0, size_hint=(0.15, 0.15), size_hint_max=(60, 60), size_hint_min=(40, 40))
            btn.bind(on_release=self.disappear_menu_list)
            # btn.bind(on_release=call_back)
            setattr(btn, 'related_call_back', call_back)
            btn.disabled = True
            self.add_widget(btn)
            self.menu_list_btns.append(btn)

            with self.canvas:
                Color(0, 1, 1, 1)
                self.connect_lines.append(Line(points=(0, 0, 0, 0)))    # just sample values in points.

            self.btn_menu = Button(text='Menu', italic=True, bold=True, color=(0, 1, 1, 1), background_color=(0, 0, 0, 0), size_hint=(0.15, 0.15), size_hint_max=(60, 60), size_hint_min=(40, 40), pos_hint={'center_x': 0.5, 'center_y': 0.5})
            self.btn_menu.bind(on_release=self.menu_action)
            self.add_widget(self.btn_menu)


    def menu_action(self, *a):
        self.disappear_menu_list() if self.is_menu_open else self.appear_menu_list()


    def appear_menu_list(self, *a):
        if Cache.get('my_global_data', 'sound_state'):
            sound = Cache.get('my_global_data', 'menu_click_sound')
            if sound:
                sound.play()

        Cache.get('my_global_data', 'vibrate_after_checking')()

        menu_list_len = len(self.menu_list)
        w = min(*self.size)
        r = w / 2 * self.menu_list_radius_hint
        cx, cy = self.size[0] / 2, self.size[1] / 2
        x0, y0 = r, 0
        xx0, yy0 = w / 2 * self.line_start_away_hint, 0
        theta = math.radians(self.start_angle)
        x1, y1 = x0 * math.cos(theta) - y0 * math.sin(theta), y0 * math.cos(theta) + x0 * math.sin(theta)
        xx1, yy1 = xx0 * math.cos(theta) - yy0 * math.sin(theta), yy0 * math.cos(theta) + xx0 * math.sin(theta)

        theta = math.radians(360 / menu_list_len)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)

        anims = [None] * menu_list_len
        anim_lines = [None] * menu_list_len

        dd = 5
        tran = self.trans[randint(0, len(self.trans) - 1)]

        for i in range(menu_list_len):
            anims[i] = Animation(center=(cx+x1, cy+y1), opacity=1, d=self.total_duration, t=tran)
            dx = dd if x1 > 0 else -dd
            dy = dd if y1 > 0 else -dd
            anim_lines[i] = Animation(points=[cx + xx1, cy + yy1, cx + x1 - dx, cy + y1 - dy], d=self.total_duration, t=tran)
            x0, y0 = x1, y1
            x1, y1 = x0 * cos_theta - y0 * sin_theta, y0 * cos_theta + x0 * sin_theta
            xx0, yy0 = xx1, yy1
            xx1, yy1 = xx0 * cos_theta - yy0 * sin_theta, yy0 * cos_theta + xx0 * sin_theta

        for btn in self.menu_list_btns:
            btn.center = cx, cy
            btn.disabled = False
            Animation.cancel_all(btn)

        for line in self.connect_lines:
            line.points = (cx, cy, cx + 1, cy + 1)
            Animation.cancel_all(line)

        with self.canvas:
            Color(0, 1, 1, 1)
            menu_ellipse = Ellipse(pos=(cx-w/4, cy-w/4), size=(w/2, w/2), angle_start=0, angle_end=360)
        anim = Animation(pos=(cx-w/14, cy-w/14), size=(w/7, w/7), d=self.total_duration)
        anim.start(menu_ellipse)
        anim.bind(on_complete=lambda *a: self.canvas.remove(menu_ellipse))

        for i in range(menu_list_len):
            anims[i].start(self.menu_list_btns[i])
            anim_lines[i].start(self.connect_lines[i])

        self.is_menu_open = True


    def do_call_back(self, cb, *a):
        if not self.is_menu_list_callback_called:
            cb()
            self.is_menu_list_callback_called = True


    def disappear_menu_list(self, *a):
        if Cache.get('my_global_data', 'sound_state'):
            sound = Cache.get('my_global_data', 'menu_close_sound')
            if sound:
                sound.play()

        cx, cy = self.size[0] / 2, self.size[1] / 2
        tran = self.trans[randint(0, len(self.trans)-1)]
        anim = Animation(center=(cx, cy), opacity=0, d=self.total_duration, t=tran)
        anim_line = Animation(points=(cx, cy, cx+1, cy+1), d=self.total_duration, t=tran)

        if len(a):      # If not by 'menu' btn
            self.is_menu_list_callback_called = False
            anim.bind(on_complete=partial(self.do_call_back, a[0].related_call_back))

        for btn in self.menu_list_btns:
            btn.disabled = True
            Animation.cancel_all(btn)
            anim.start(btn)

        for line in self.connect_lines:
            Animation.cancel_all(line)
            anim_line.start(line)

        self.is_menu_open = False


class HomeScreenLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(HomeScreenLayout, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0.25, 0, 0, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_rect, pos=self.update_rect)

        w, h = Window.size
        self.menu = Menu(size_hint=(1, w / h), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.menu.set_attributes(start_angle=18, menu_list_radius_hint=0.6, line_start_away_hint=0.1, total_duration=0.5, menu_list=(('Game', self.go_to_game_screen), ('Settings', self.go_to_settings_screen), ("Records", self.go_to_records_screen), ('About', self.go_to_about_screen), ('Exit', self.exit)))
        self.add_widget(self.menu)

        self.bind(on_touch_move=self.on_touch_move_do)

        # Popup feature...
        popup_start = Popup(title='Sound  &  Vibration', title_color=(0, 1, 1, 1), separator_height=2, title_align='center', size_hint=(0.9, 0.4), auto_dismiss=False)

        layout = RelativeLayout()
        label_sound = Label(text='Sound :', bold=True, italic=True, color=(0.2, 0, 1, 1), size_hint=(0.5, 0.3), pos_hint={'x': 0, 'y': 0.6})
        switch_sound = Switch(active=True, size_hint=(0.5, 0.3), pos_hint={'x': 0.5, 'y': 0.6})
        label_vibration = Label(text='Vibration :', bold=True, italic=True, color=(0.2, 0, 1, 1), size_hint=(0.5, 0.3), pos_hint={'x': 0, 'y': 0.35})
        switch_vibration = Switch(active=True, size_hint=(0.5, 0.3), pos_hint={'x': 0.5, 'y': 0.35})
        btn_ok = Button(text='OK', bold=True, color=(0, 0, 1, 1), background_color=(0, 0, 0, 0.15), size_hint=(0.5, 0.25), pos_hint={'x': 0.25, 'y': 0.05})

        def popup_ok_btn_do(*a):
            if not switch_sound.active:
                Cache.append('my_global_data', 'sound_state', False)
                self.parent.manager.settings_screen_layout.sound_switch.active = False

            if not switch_vibration.active:
                Cache.append('my_global_data', 'vibration_state', False)
                self.parent.manager.settings_screen_layout.vibration_switch.active = False

            def after_anim_completion_do(*a):
                popup_start.dismiss()

                if Cache.get('my_global_data', 'sound_state'):
                    sound = Cache.get('my_global_data', 'tic_tac_toe_sound')
                    if sound:
                        sound.play()

                Clock.schedule_once(self.menu.appear_menu_list, 1)


            anim2 = Animation(size_hint=(1, 1), d=0.5) + Animation(size_hint=(0.1, 0.1), opacity=0, d=0.5)
            anim2.bind(on_complete=after_anim_completion_do)
            anim2.start(popup_start)

        btn_ok.bind(on_release=popup_ok_btn_do)

        layout.add_widget(Image(source='images/popup_background.png', allow_stretch=True, keep_ratio=False))
        layout.add_widget(label_sound)
        layout.add_widget(switch_sound)
        layout.add_widget(label_vibration)
        layout.add_widget(switch_vibration)
        layout.add_widget(btn_ok)

        popup_start.content = layout

        anim = Animation(size_hint=(1, 1), opacity=1, d=0.75) + Animation(size_hint=(0.9, 0.4), d=0.5)
        popup_start.bind(on_open=lambda *a: anim.start(popup_start))
        popup_start.size_hint = (0.1, 0.1)
        popup_start.opacity = 0

        Clock.schedule_once(popup_start.open, 0)    # Execute popup_start.open() in next frame.


    def update_rect(self, *a):
        self.rect.size = self.size
        self.rect.pos = self.pos


    def on_touch_move_do(self, touch, *a):
        if not self.menu.is_menu_open:
            self.menu.appear_menu_list()


    def go_to_game_screen(self, *a):
        self.parent.parent.transition.direction = 'left'
        self.parent.parent.current = 'game_screen'


    def go_to_settings_screen(self, *a):
        self.parent.parent.transition.direction = 'left'
        self.parent.parent.current = 'settings_screen'


    def go_to_records_screen(self, *a):
        self.parent.parent.transition.direction = 'left'
        self.parent.parent.current = 'records_screen'


    def go_to_about_screen(self, *a):
        self.parent.parent.transition.direction = 'left'
        self.parent.parent.current = 'about_screen'


    def exit(self, *a):
        exit()


class RecordsScreenLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(RecordsScreenLayout, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0, 1, 1, 0.5)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_rect, pos=self.update_rect)

        self.popup_ask_to_reset = Popup(title='Reset ?', title_color=(0, 1, 1, 1), separator_height=2, title_align='center', size_hint=(0.9, 0.4), auto_dismiss=False)

        layout = RelativeLayout()
        dialogue = Label(text='Do you want to reset all records ?', bold=True, italic=True, color=(0.2, 0, 1, 1), size_hint=(1, 0.20), pos_hint={'x': 0, 'y': 0.5})
        btn_yes = Button(text='Yes', on_release=self.popup_ask_to_reset.dismiss, color=(0.2, 0, 1, 1), background_color=(0, 0, 0, 0.15), size_hint=(0.25, 0.20), pos_hint={'x': 0.25, 'y': 0.25})
        btn_yes.bind(on_release=self.reset_records)
        btn_no = Button(text='No', on_release=self.popup_ask_to_reset.dismiss, color=(0.2, 0, 1, 1), background_color=(0, 0, 0, 0.15), size_hint=(0.25, 0.20), pos_hint={'x': 0.51, 'y': 0.25})

        layout.add_widget(Image(source='images/popup_background.png', allow_stretch=True, keep_ratio=False))
        layout.add_widget(dialogue)
        layout.add_widget(btn_yes)
        layout.add_widget(btn_no)

        self.popup_ask_to_reset.content = layout
        self.popup_ask_to_reset.bind(on_open=Cache.get('my_global_data', 'vibrate_after_checking'))

        store = Cache.get('my_global_data', 'records_store')

        N = 13
        bengali_font_path = Cache.get('my_global_data', 'bengali_font_path')

        self.btn_back = Button(text='Home', color=(0, 1, 1, 1), on_release=self.go_to_home_screen, size_hint=(0.5, 1/N), pos_hint={'x': 0, 'y': 1/N*(N-1)})
        self.btn_reset = Button(text='Reset', color=(0, 1, 1, 1), on_release=self.popup_ask_to_reset.open, size_hint=(0.5, 1/N), pos_hint={'x': 0.5, 'y': 1/N*(N-1)})

        self.label_single_mode = Label(text='SINGLE MODE', bold=True, italic=True, size_hint=(1, 1/N), pos_hint={'x': 0, 'y': 1/N*(N-2)})

        self.label_difficulty = Label(text='Difficulty', bold=True, italic=True, underline=True, size_hint=(1/4, 1/N), pos_hint={'x': 0, 'y': 1/N*(N-3)})
        self.label_player = Label(text='Player', bold=True, italic=True, underline=True, size_hint=(1/4, 1/N), pos_hint={'x': 1/4, 'y': 1/N*(N-3)})
        self.label_cpu = Label(text='CPU', bold=True, italic=True, underline=True, size_hint=(1/4, 1/N), pos_hint={'x': 1/4*2, 'y': 1/N*(N-3)})
        self.label_player_name = Label(text='Name', bold=True, italic=True, underline=True, size_hint=(1/4, 1/N), pos_hint={'x': 1/4*3, 'y': 1/N*(N-3)})

        info = store.get('easy')
        self.label_easy = Label(text='Easy :', italic=True, size_hint=(1/4, 1/N), pos_hint={'x': 0, 'y': 1/N*(N-4)})
        self.label_easy_player_score = Label(text=str(info['player_score']), italic=True, size_hint=(1/4, 1/N), pos_hint={'x': 1/4, 'y': 1/N*(N-4)})
        self.label_easy_cpu_score = Label(text=str(info['cpu_score']), italic=True, size_hint=(1/4, 1/N), pos_hint={'x': 1/4*2, 'y': 1/N*(N-4)})
        self.label_easy_player_name = Label(text=info['player_name'], italic=True, font_name=bengali_font_path, size_hint=(1/4, 1/N), pos_hint={'x': 1/4*3, 'y': 1/N*(N-4)})

        info = store.get('medium')
        self.label_medium = Label(text='Medium :', italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 5)})
        self.label_medium_player_score = Label(text=str(info['player_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4, 'y': 1 / N * (N - 5)})
        self.label_medium_cpu_score = Label(text=str(info['cpu_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 2, 'y': 1 / N * (N - 5)})
        self.label_medium_player_name = Label(text=info['player_name'], italic=True, font_name=bengali_font_path, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 3, 'y': 1 / N * (N - 5)})

        info = store.get('hard')
        self.label_hard = Label(text='Hard :', italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 6)})
        self.label_hard_player_score = Label(text=str(info['player_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4, 'y': 1 / N * (N - 6)})
        self.label_hard_cpu_score = Label(text=str(info['cpu_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 2, 'y': 1 / N * (N - 6)})
        self.label_hard_player_name = Label(text=info['player_name'], italic=True, font_name=bengali_font_path, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 3, 'y': 1 / N * (N - 6)})

        info = store.get('intense')
        self.label_intense = Label(text='Intense :', italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 7)})
        self.label_intense_player_score = Label(text=str(info['player_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4, 'y': 1 / N * (N - 7)})
        self.label_intense_cpu_score = Label(text=str(info['cpu_score']), italic=True, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 2, 'y': 1 / N * (N - 7)})
        self.label_intense_player_name = Label(text=info['player_name'], italic=True, font_name=bengali_font_path, size_hint=(1 / 4, 1 / N), pos_hint={'x': 1 / 4 * 3, 'y': 1 / N * (N - 7)})

        self.label_dual_mode = Label(text='DUAL MODE', bold=True, italic=True, size_hint=(1, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 8)})

        self.label_dual_player1 = Label(text='Player-1', bold=True, italic=True, underline=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3, 'y': 1 / N * (N - 9)})
        self.label_dual_player2 = Label(text='Player-2', bold=True, italic=True, underline=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3 * 2, 'y': 1 / N * (N - 9)})

        info = store.get('dual')
        self.label_dual_score = Label(text='Score :', italic=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 10)})
        self.label_dual_player1_score = Label(text=str(info['player1_score']), italic=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3, 'y': 1 / N * (N - 10)})
        self.label_dual_player2_score = Label(text=str(info['player2_score']), italic=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3 * 2, 'y': 1 / N * (N - 10)})

        self.label_dual_name = Label(text='Name :', italic=True, size_hint=(1 / 3, 1 / N), pos_hint={'x': 0, 'y': 1 / N * (N - 11)})
        self.label_dual_player1_name = Label(text=info['player1_name'], italic=True, font_name=bengali_font_path, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3, 'y': 1 / N * (N - 11)})
        self.label_dual_player2_name = Label(text=info['player2_name'], italic=True, font_name=bengali_font_path, size_hint=(1 / 3, 1 / N), pos_hint={'x': 1 / 3 * 2, 'y': 1 / N * (N - 11)})

        self.btn_back.bind(on_release=Cache.get('my_global_data', 'play_button_press_sound'))
        self.btn_reset.bind(on_release=Cache.get('my_global_data', 'play_button_press_sound'))

        self.add_widget(self.btn_back)
        self.add_widget(self.btn_reset)
        self.add_widget(self.label_single_mode)
        self.add_widget(self.label_difficulty)
        self.add_widget(self.label_player)
        self.add_widget(self.label_cpu)
        self.add_widget(self.label_player_name)
        self.add_widget(self.label_easy)
        self.add_widget(self.label_easy_player_score)
        self.add_widget(self.label_easy_cpu_score)
        self.add_widget(self.label_easy_player_name)
        self.add_widget(self.label_medium)
        self.add_widget(self.label_medium_player_score)
        self.add_widget(self.label_medium_cpu_score)
        self.add_widget(self.label_medium_player_name)
        self.add_widget(self.label_hard)
        self.add_widget(self.label_hard_player_score)
        self.add_widget(self.label_hard_cpu_score)
        self.add_widget(self.label_hard_player_name)
        self.add_widget(self.label_intense)
        self.add_widget(self.label_intense_player_score)
        self.add_widget(self.label_intense_cpu_score)
        self.add_widget(self.label_intense_player_name)
        self.add_widget(self.label_dual_mode)
        self.add_widget(self.label_dual_player1)
        self.add_widget(self.label_dual_player2)
        self.add_widget(self.label_dual_score)
        self.add_widget(self.label_dual_player1_score)
        self.add_widget(self.label_dual_player2_score)
        self.add_widget(self.label_dual_name)
        self.add_widget(self.label_dual_player1_name)
        self.add_widget(self.label_dual_player2_name)


    def update_rect(self, *a):
        self.rect.size = self.size
        self.rect.pos = self.pos


    def go_to_home_screen(self, *a):
        self.parent.parent.transition.direction = 'right'
        self.parent.parent.current = 'home_screen'


    def reset_records(self, *a):
        store = Cache.get('my_global_data', 'records_store')

        for difficulty in ('easy', 'medium', 'hard', 'intense'):
            prefix = 'label_' + difficulty
            setattr(getattr(self, prefix + '_player_score'), 'text', '0')
            setattr(getattr(self, prefix + '_cpu_score'), 'text', '0')
            setattr(getattr(self, prefix + '_player_name'), 'text', '-')
            store.put(difficulty, player_score=0, cpu_score=0, player_name='-')

        self.label_dual_player1_score.text = '0'
        self.label_dual_player2_score.text = '0'
        self.label_dual_player1_name.text = '-'
        self.label_dual_player2_name.text = '-'
        store.put('dual', player1_score=0, player2_score=0, player1_name='-', player2_name='-')


class AboutScreenLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(AboutScreenLayout, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0, 1, 1, 0.5)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_rect, pos=self.update_rect)

        self.btn_back = Button(text='Back', color=(0, 1, 1, 1), on_release=self.go_to_home_screen, size_hint=(0.25, 0.1), pos_hint={'x': 0, 'y': 0.9})
        self.app_ver = Label(text="Tic Tac Toe Extend    0.1", bold=True, italic=True, color=(0.25, 1, 0.5, 1), halign='center', size_hint=(1, 0.1), pos_hint={'x': 0, 'y': 0.8})
        self.label_dev = Label(text="[i][u][b]Developed by:[/b][/u]\nMd. Shahedul Islam Shahed\nshahed.shd777@gmail.com[/i]", markup=True, color=(0.25, 1, 1, 1), halign='center', size_hint=(1, 0.1), pos_hint={'x': 0, 'y': 0.7})

        self.add_widget(self.btn_back)
        self.add_widget(self.app_ver)
        self.add_widget(self.label_dev)


    def update_rect(self, *a):
        self.rect.size = self.size
        self.rect.pos = self.pos


    def go_to_home_screen(self, *a):
        Cache.get('my_global_data', 'play_button_press_sound')()

        self.parent.parent.transition.direction = 'right'
        self.parent.parent.current = 'home_screen'


class MyScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)

        home_scr = Screen(name='home_screen')
        game_scr = Screen(name='game_screen')
        settings_scr = Screen(name='settings_screen')
        records_scr = Screen(name='records_screen')
        about_scr = Screen(name='about_screen')

        self.home_screen_layout = HomeScreenLayout()
        self.game_screen_layout = GameScreenLayout()
        self.settings_screen_layout = SettingsScreenLayout()
        self.records_screen_layout = RecordsScreenLayout()
        self.about_screen_layout = AboutScreenLayout()

        home_scr.add_widget(self.home_screen_layout)
        settings_scr.add_widget(Image(source='images/settings_screen_background.png', allow_stretch=True, keep_ratio=False, color=(1, 1, 1, 0.5)))
        settings_scr.add_widget(self.settings_screen_layout)
        game_scr.add_widget(self.game_screen_layout)
        records_scr.add_widget(self.records_screen_layout)
        about_scr.add_widget(self.about_screen_layout)

        self.add_widget(home_scr)
        self.add_widget(game_scr)
        self.add_widget(settings_scr)
        self.add_widget(records_scr)
        self.add_widget(about_scr)

        home_scr.bind(on_enter=lambda *a: Clock.schedule_once(self.home_screen_layout.menu.appear_menu_list, 0.25))
        Cache.append('my_global_data', 'game_screen_layout', self.game_screen_layout)
        Cache.append('my_global_data', 'records_screen_layout', self.records_screen_layout)


class Tic_Tac_Toe_Extend(App):
    def __init__(self, **kwargs):
        super(Tic_Tac_Toe_Extend, self).__init__(**kwargs)

        self.sm = MyScreenManager()
        Window.bind(on_keyboard=self.key_handler)


    def key_handler(self, window_instance, key, *a):
        if key == 27:       # 27: 'Esc' on desktop, 'Back' on android
            if self.sm.current == 'home_screen':
                if self.sm.home_screen_layout.menu.is_menu_open:
                    self.sm.home_screen_layout.menu.disappear_menu_list()
            else:
                self.sm.transition.direction = 'right'
                self.sm.current = 'home_screen'
        elif key in (1073741942, 82):     # 1073741942: Menu on desktop (linux mint)
            if self.sm.current == 'home_screen':
                self.sm.home_screen_layout.menu.menu_action()

        return True


    def build(self):
        if platform == 'android':
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            activity.removeLoadingScreen()

        return self.sm


def main():
    Cache.register('my_global_data')
    Cache.append('my_global_data', 'board_dimension', 3)
    Cache.append('my_global_data', 'player_icon_list', listdir('images/player_icons'))
    Cache.append('my_global_data', 'player1_icon_name', 'player_icon_1.png')
    Cache.append('my_global_data', 'player2_icon_name', 'player_icon_2.png')
    Cache.append('my_global_data', 'match_type', Enum('MatchType', "H_top H_mid H_bottom V_left V_mid V_right D_tl_br D_tr_bl No_match"))
    Cache.append('my_global_data', 'board_state', BoardState())
    Cache.append('my_global_data', 'game_manager', GameManager())
    Cache.append('my_global_data', 'record_manager', RecordManager())
    Cache.append('my_global_data', 'whose_turn', 1)             # possible values 0, 1, 2
    Cache.append('my_global_data', 'player_winner', 0)          # Will be set correctly when someone wins.
    Cache.append('my_global_data', 'game_difficulty', 2)        # 1: Easy, 2: Medium, 3: Hard, 4: Intense
    Cache.append('my_global_data', 'player_mood', 1)            # 1: Single 2: Dual
    Cache.append('my_global_data', 'sound_state', True)         # True or False
    Cache.append('my_global_data', 'vibration_state', True)     # True or False
    Cache.append('my_global_data', 'tic_tac_toe_sound', SoundLoader.load('audios/tic_tac_toe.wav'))
    Cache.append('my_global_data', 'menu_click_sound', SoundLoader.load('audios/menu_click.wav'))
    Cache.append('my_global_data', 'menu_close_sound', SoundLoader.load('audios/menu_close.wav'))
    Cache.append('my_global_data', 'popup_winner_sound', SoundLoader.load('audios/popup_winner.wav'))
    Cache.append('my_global_data', 'popup_draw_sound', SoundLoader.load('audios/popup_draw.wav'))
    Cache.append('my_global_data', 'button_press_sound', SoundLoader.load('audios/button_press.wav'))
    Cache.append('my_global_data', 'bengali_font_path', 'others/muktinarrow.ttf')
    Cache.append('my_global_data', 'records_store', DictStore('others/records.txt'))

    # 'easy': {'player_score': 0, 'player_name': '-', 'cpu_score': 0}
    # 'medium': {'player_score': 0, 'player_name': '-', 'cpu_score': 0}
    # 'hard': {'player_score': 0, 'player_name': '-', 'cpu_score': 0}
    # 'dual': {'player1_score': 0, 'player2_name': '-', 'player1_name': '-', 'player2_score': 0}

    def play_button_press_sound(*a):
        if Cache.get('my_global_data', 'sound_state'):
            sound = Cache.get('my_global_data', 'button_press_sound')
            if sound:
                sound.play()

    def vibrate_after_checking(*a):
        if Cache.get('my_global_data', 'vibration_state'):
            try:
                vibrator.vibrate(0.25)
            except:
                print("Vibration not working. Got exception.")

    Cache.append('my_global_data', 'play_button_press_sound', play_button_press_sound)
    Cache.append('my_global_data', 'vibrate_after_checking', vibrate_after_checking)

    # more appended to Cache 'my_global_data':
    # 'game_screen_layout'
    # 'game_layout_topbox'
    # 'game_layout_bottombox'
    # 'game_layout_board_wrapper'
    # 'records_screen_layout'

    if platform in ('win', 'linux', 'macosx', 'unknown'):
        factor = 40
        Window.size = (9*factor, 16*factor)

    app = Tic_Tac_Toe_Extend()
    app.run()


if __name__ == '__main__':
    main()
