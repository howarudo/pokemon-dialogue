import pygame
from pygame.locals import *
import time
import math
import random
import requests
import io
from urllib.request import urlopen
import subprocess
import os
import logging
import re  # 正規表現で出力を解析する

pygame.init()
# create the game window
game_width = 500
game_height = 500
size = (game_width, game_height)
game = pygame.display.set_mode(size)
pygame.display.set_caption('Pokemon Battle')

vs_sound = "pokemon_dialogue/vstrainer.wav"
win_sound = "pokemon_dialogue/winpokemon.wav"
is_battle_music_playing = False

# define colors
black = (0, 0, 0)
gold = (218, 165, 32)
grey = (200, 200, 200)
green = (0, 200, 0)
red = (200, 0, 0)
white = (255, 255, 255)

# base url of the API
base_url = 'https://pokeapi.co/api/v2'

class Move():

    def __init__(self, url):

        # call the moves API endpoint
        req = requests.get(url)
        self.json = req.json()

        self.name = self.json['name']
        self.power = self.json['power']
        self.type = self.json['type']['name']

class Pokemon(pygame.sprite.Sprite):

    def __init__(self, name, level, x, y):

        pygame.sprite.Sprite.__init__(self)

        # call the pokemon API endpoint
        req = requests.get(f'{base_url}/pokemon/{name.lower()}')
        self.json = req.json()

        # set the pokemon's name and level
        self.name = name
        self.level = level

        # set the sprite position on the screen
        self.x = x
        self.y = y

        # number of potions left
        self.num_potions = 3

        # get the pokemon's stats from the API
        stats = self.json['stats']
        for stat in stats:
            if stat['stat']['name'] == 'hp':
                self.current_hp = stat['base_stat'] + self.level
                self.max_hp = stat['base_stat'] + self.level
            elif stat['stat']['name'] == 'attack':
                self.attack = stat['base_stat']
            elif stat['stat']['name'] == 'defense':
                self.defense = stat['base_stat']
            elif stat['stat']['name'] == 'speed':
                self.speed = stat['base_stat']

        # set the pokemon's types
        self.types = []
        for i in range(len(self.json['types'])):
            type = self.json['types'][i]
            self.types.append(type['type']['name'])

        # set the sprite's width
        self.size = 150

        # set the sprite to the front facing sprite
        self.set_sprite('front_default')

    def perform_attack(self, other, move):
        try:
            display_message(f'{english_to_japanese[self.name]}の　{english_to_japanese_moves[move.name]}　攻撃！')
        
        except KeyError:
            display_message('リザードンは　ほのおのうずを　はいた！')

        # pause for 2 seconds
        waitFor(2000)

        # calculate the damage
        damage = (2 * self.level + 10) / 250 * self.attack / other.defense * move.power

        # same type attack bonus (STAB)
        if move.type in self.types:
            damage *= 1.5

        # critical hit (6.25% chance)
        random_num = random.randint(1, 5000)
        if random_num <= 625:
            damage *= 1.5

        # round down the damage
        damage = math.floor(damage)

        other.take_damage(damage)

    def take_damage(self, damage):

        self.current_hp -= damage

        # hp should not go below 0
        if self.current_hp < 0:
            self.current_hp = 0

    def use_potion(self):

        # check if there are potions left
        if self.num_potions > 0:

            # add 30 hp (but don't go over the max hp)
            self.current_hp += 30
            if self.current_hp > self.max_hp:
                self.current_hp = self.max_hp

            # decrease the number of potions left
            self.num_potions -= 1

    def set_sprite(self, side):

        # set the pokemon's sprite
        image = self.json['sprites'][side]
        image_stream = urlopen(image).read()
        image_file = io.BytesIO(image_stream)
        self.image = pygame.image.load(image_file).convert_alpha()

        # scale the image
        scale = self.size / self.image.get_width()
        new_width = self.image.get_width() * scale
        new_height = self.image.get_height() * scale
        self.image = pygame.transform.scale(self.image, (new_width, new_height))

    def set_moves(self):

        self.moves = []

        # go through all moves from the api
        for i in range(len(self.json['moves'])):

            # get the move from different game versions
            versions = self.json['moves'][i]['version_group_details']
            for j in range(len(versions)):

                version = versions[j]

                # only get moves from red-blue version
                if version['version_group']['name'] != 'red-blue':
                    continue

                # only get moves that can be learned from leveling up (ie. exclude TM moves)
                learn_method = version['move_learn_method']['name']
                if learn_method != 'level-up':
                    continue

                # add move if pokemon level is high enough
                level_learned = version['level_learned_at']
                if self.level >= level_learned:
                    move = Move(self.json['moves'][i]['move']['url'])

                    # only include attack moves
                    if move.power is not None:
                        self.moves.append(move)

        # select up to 4 random moves
        if len(self.moves) > 4:
            self.moves = random.sample(self.moves, 4)

    def draw(self, alpha=255):

        sprite = self.image.copy()
        transparency = (255, 255, 255, alpha)
        sprite.fill(transparency, None, pygame.BLEND_RGBA_MULT)
        game.blit(sprite, (self.x, self.y))

    def draw_hp(self):

        # display the health bar
        bar_scale = 200 // self.max_hp
        for i in range(self.max_hp):
            bar = (self.hp_x + bar_scale * i, self.hp_y, bar_scale, 20)
            pygame.draw.rect(game, red, bar)

        for i in range(self.current_hp):
            bar = (self.hp_x + bar_scale * i, self.hp_y, bar_scale, 20)
            pygame.draw.rect(game, green, bar)

        # display "HP" text
        font = pygame.font.Font(pygame.font.get_default_font(), 16)
        text = font.render(f'HP: {self.current_hp} / {self.max_hp}', True, black)
        text_rect = text.get_rect()
        text_rect.x = self.hp_x
        text_rect.y = self.hp_y + 30
        game.blit(text, text_rect)

    def get_rect(self):

        return Rect(self.x, self.y, self.image.get_width(), self.image.get_height())


#フォントパスの指定
font_path = "PixelMplus-20130602/PixelMplus12-Regular.ttf"

def display_message(message):

    # draw a white box with black border
    pygame.draw.rect(game, white, (10, 350, 480, 140))
    pygame.draw.rect(game, black, (10, 350, 480, 140), 3)

    # display the message
    font = pygame.font.Font(font_path, 18)
    text = font.render(message, True, black)
    text_rect = text.get_rect()
    text_rect.x = 30
    text_rect.y = 410
    game.blit(text, text_rect)

    pygame.display.update()

def create_button(width, height, left, top, text_cx, text_cy, label):
    button = Rect(left, top, width, height)

    # highlight the button if mouse is pointing to it
    pygame.draw.rect(game, white, button)

    # add the label to the button
    font = pygame.font.Font(font_path, 16)  # 日本語対応フォントを指定
    text = font.render(f'{label}', True, black)
    text_rect = text.get_rect(center=(text_cx, text_cy))
    game.blit(text, text_rect)

    return button

# Add the waitFor function
def waitFor(milliseconds):
    """ Wait for the given time period, but handling some events """
    time_now = pygame.time.get_ticks()   # zero point
    finish_time = time_now + milliseconds   # finish time

    while time_now < finish_time:
        # Handle user-input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))  # re-post to handle in the main loop
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                break
        pygame.display.update()  # Ensure display updates
        pygame.time.wait(200)  # save some CPU for a split-second
        time_now = pygame.time.get_ticks()  # update the current time


# create the starter pokemons
level = 30
bulbasaur = Pokemon('Bulbasaur', level, 25, 150)
charmander = Pokemon('Charmander', level, 175, 150)
squirtle = Pokemon('Squirtle', level, 325, 150)
pokemons = [bulbasaur, charmander, squirtle]

# the player's and rival's selected pokemon
player_pokemon = None
rival_pokemon = None

# ポケモンの名前を英語から日本語へ直す辞書
english_to_japanese = {
    'Bulbasaur': 'フシギダネ',
    'Charmander':'ヒトカゲ',
    'Squirtle': 'ゼニガメ',
    }

#わざの名前を英語から日本語へ直す辞書
english_to_japanese_moves = {'vine-whip': 'つるのムチ',
                             'tackle': 'たいあたり',
                             'razor-leaf': 'はっぱカッター',
                             'scratch': 'ひっかく',
                             'ember': 'ひのこ',
                             'rage': 'いかり',
                             'slash': 'きりさく',
                             'bite': 'かみつく',
                             'water-gun': 'みずでっぽう',
                             'bubble': 'あわ'}


# game loop
game_status = 'select pokemon'
while game_status != 'quit':

    for event in pygame.event.get():
        if event.type == QUIT:
            game_status = 'quit'

        # detect keypress
        if event.type == KEYDOWN:

            # play again
            if event.key == K_y:
                # reset the pokemons
                bulbasaur = Pokemon('Bulbasaur', level, 25, 150)
                charmander = Pokemon('Charmander', level, 175, 150)
                squirtle = Pokemon('Squirtle', level, 325, 150)
                pokemons = [bulbasaur, charmander, squirtle]
                game_status = 'select pokemon'

            # quit
            elif event.key == K_n:
                game_status = 'quit'

    # pokemon select screen
    if game_status == 'select pokemon':

        game.fill(white)

        # draw the starter pokemons
        bulbasaur.draw()
        charmander.draw()
        squirtle.draw()

        pygame.display.update()

        waitFor(1000)


        julius_command = [
            "julius",
            "-C",
            "dialogue-demo/asr/grammar-mic.jconf",
            "-input",
            "mic"
        ]

        try:
            process = subprocess.Popen(
                julius_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            while True:
                line = process.stdout.readline()
                if line:
                    # "sentence1:" で始まる行を取得
                    match = re.match(r"sentence1:\s*(.*)", line)
                    if match:
                        result = match.group(1).strip()
                        print(f"認識結果: {result}")  # デバッグ用出力
                        if "フシギダネ" in result:
                            player_pokemon = pokemons[0]
                            rival_pokemon = pokemons[1]
                        elif "ヒトカゲ" in result:
                            player_pokemon = pokemons[1]
                            rival_pokemon = pokemons[2]
                        elif "ゼニガメ" in result:
                            player_pokemon = pokemons[2]
                            rival_pokemon = pokemons[0]
                        else:
                            continue
                        # lower the rival pokemon's level to make the battle easier
                        rival_pokemon.level = int(rival_pokemon.level * .75)
                        player_pokemon.hp_x = 275
                        player_pokemon.hp_y = 250
                        rival_pokemon.hp_x = 50
                        rival_pokemon.hp_y = 50

                        game_status = 'prebattle'
                        break
                if process.poll() is not None:
                    print("Julius プロセスが終了しました")
                    break
        except Exception as e:
            print(f"Julius 実行中にエラーが発生しました: {str(e)}")
            display_message("音声認識に失敗しました。リトライしてください。")

        pygame.display.update()

    # get moves from the API and reposition the pokemons
    if game_status == 'prebattle':
        if not is_battle_music_playing:
            pygame.mixer.music.load(vs_sound)
            pygame.mixer.music.play(-1)  # 無限ループ再生
            is_battle_music_playing = True


        # draw the selected pokemon
        game.fill(white)
        player_pokemon.draw()
        pygame.display.update()

        player_pokemon.set_moves()
        rival_pokemon.set_moves()

        # reposition the pokemons
        player_pokemon.x = -50
        player_pokemon.y = 100
        rival_pokemon.x = 250
        rival_pokemon.y = -50

        # resize the sprites
        player_pokemon.size = 300
        rival_pokemon.size = 300
        player_pokemon.set_sprite('back_default')
        rival_pokemon.set_sprite('front_default')

        game_status = 'start battle'

        pygame.display.update()

    # start battle animation
    if game_status == 'start battle':

        # rival sends out their pokemon
        alpha = 0
        while alpha < 255:

            game.fill(white)
            rival_pokemon.draw(alpha)
            if rival_pokemon.name == 'Bulbasaur':
                display_message('ライバルは　フシギダネを　くりだした！!')
            elif rival_pokemon.name == 'Charmander':
                display_message('ライバルは　ヒトカゲを　くりだした！')
            elif rival_pokemon.name == 'Squirtle':
                display_message('ライバルは　ゼニガメを　くりだした！')
            alpha += .4

            pygame.display.update()

        # pause for 1 second
        waitFor(1000)

        # player sends out their pokemon
        alpha = 0
        while alpha < 255:

            game.fill(white)
            rival_pokemon.draw()
            player_pokemon.draw(alpha)
            if player_pokemon.name == 'Bulbasaur':
                display_message('ゆけっ！　フシギダネ！')
            elif player_pokemon.name == 'Charmander':
                display_message('ゆけっ！　ヒトカゲ！')
            elif player_pokemon.name == 'Squirtle':
                display_message('ゆけっ！　ゼニガメ！')
            alpha += .4

            pygame.display.update()

        # draw the hp bars
        player_pokemon.draw_hp()
        rival_pokemon.draw_hp()

        # determine who goes first
        if rival_pokemon.speed > player_pokemon.speed:
            game_status = 'rival turn'
        else:
            game_status = 'player turn'

        pygame.display.update()

        # pause for 1 second
        waitFor(1000)

    # display the fight and use potion buttons
    if game_status == 'player turn':
        game.fill(white)
        player_pokemon.draw()
        rival_pokemon.draw()
        player_pokemon.draw_hp()
        rival_pokemon.draw_hp()

        # ボタンを使わない表示にする場合
        display_message(f'{english_to_japanese[player_pokemon.name]}は　どうする？（たたかう　かいふく）')

        # draw the black border
        pygame.draw.rect(game, black, (10, 350, 480, 140), 3)

        pygame.display.update()

        # Julius コマンドを直接実行
        julius_command = [
            "julius",
            "-C",
            "dialogue-demo/asr/grammar-mic.jconf",
            "-input",
            "mic"
        ]

        try:
            process = subprocess.Popen(
                julius_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 音声認識の結果をリアルタイムで取得
            while True:
                line = process.stdout.readline()
                if line:
                    # "sentence1:" で始まる行を取得
                    match = re.match(r"sentence1:\s*(.*)", line)
                    if match:
                        result = match.group(1).strip()
                        print(f"認識結果: {result}")  # デバッグ用出力

                        # 音声認識結果に応じてゲームロジックを実行
                        if "たたかう" in result or "いけ" in result or "ヒトカゲ" in result or "ゼニガメ" in result or "フシギダネ" in result :
                            game_status = 'player move'
                            # game_status = 'fainted'
                            break
                        elif "かいふく" in result :
                            # force to attack if there are no more potions
                            if player_pokemon.num_potions == 0:
                                display_message('キズぐすりが　ありません')
                                waitFor(500)
                                game_status = 'player move'
                            else:
                                player_pokemon.use_potion()
                                display_message('キズぐすりを　つかった！')
                                waitFor(500)
                                game_status = 'rival turn'
                            break
                # プロセスが終了した場合
                if process.poll() is not None:
                    print("Julius プロセスが終了しました")
                    break

        except Exception as e:
            print(f"Julius 実行中にエラーが発生しました: {str(e)}")
            display_message("音声認識に失敗しました。リトライしてください。")

        # 描画を更新
        pygame.display.update()

    if game_status == 'player move':
        # Julius コマンドを直接実行
        julius_command = [
            "julius",
            "-C",
            "dialogue-demo/asr/grammar-mic.jconf",
            "-input",
            "mic"
        ]

        try:
            process = subprocess.Popen(
                julius_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            game.fill(white)
            player_pokemon.draw()
            rival_pokemon.draw()
            player_pokemon.draw_hp()
            rival_pokemon.draw_hp()

            display_message("ポケモンに指示を出すんだ！！！")

            waitFor(1500)

            # create a button for each move
            for i in range(4):
                button_width = 240
                button_height = 70
                left = 10 + i % 2 * button_width
                top = 350 + i // 2 * button_height
                text_center_x = left + 120
                text_center_y = top + 35
                if i < len(player_pokemon.moves):
                    move = player_pokemon.moves[i]
                    if move.name in english_to_japanese_moves:
                        button = create_button(button_width, button_height, left, top, text_center_x, text_center_y, english_to_japanese_moves[move.name])
                    else:
                        button = create_button(button_width, button_height, left, top, text_center_x, text_center_y, move.name.capitalize())
                else:
                    button = create_button(button_width, button_height, left, top, text_center_x, text_center_y, ' ')
            # draw the black border
            pygame.draw.rect(game, black, (10, 350, 480, 140), 3)
            pygame.display.update()

            waitFor(2000)

            # 音声認識の結果をリアルタイムで取得
            while True:
                line = process.stdout.readline()
                if line:
                    # "sentence1:" で始まる行を取得
                    match = re.match(r"sentence1:\s*(.*)", line)
                    if match:
                        result = match.group(1).strip()
                        print(f"認識結果: {result}")  # デバッグ用出力

                        # 音声認識結果に応じてゲームロジックを実行
                        if "つるのムチ" in result or (player_pokemon.name == "Squirtle" and "たいあたり" in result) or "ひっかく" in result :
                            player_pokemon.perform_attack(rival_pokemon, player_pokemon.moves[0])
                            game_status = 'rival turn'
                            # game_status = 'fainted'
                            print("技" + result)
                            break
                        elif (player_pokemon.name == "Bulbasaur" and "たいあたり" in result) or "ひのこ" in result or "かみつく" in result:
                            player_pokemon.perform_attack(rival_pokemon, player_pokemon.moves[1])
                            game_status = 'rival turn'
                            # game_status = 'fainted'
                            print("技" + result)
                            break
                        elif "はっぱカッター" in result or "いかり" in result or "みずでっぽう" in result:
                            player_pokemon.perform_attack(rival_pokemon, player_pokemon.moves[2])
                            game_status = 'rival turn'
                            # game_status = 'fainted'
                            print("技" + result)
                            break
                        elif "きりさく" in result or "あわ" in result :
                            player_pokemon.perform_attack(rival_pokemon, player_pokemon.moves[3])
                            game_status = 'rival turn'
                            # game_status = 'fainted'
                            print("技" + result)
                            break

                # プロセスが終了した場合
                if process.poll() is not None:
                    print("Julius プロセスが終了しました")
                    break
            # print("ループを抜けました")

            # Julius のエラー出力を取得してデバッグ
            # stderr_output = process.stderr.read()
            # print(stderr_output)
            # if stderr_output:
            #     print(f"Julius エラー: {stderr_output}")

        except Exception as e:
            print(f"Julius 実行中にエラーが発生しました: {str(e)}")
            display_message("音声認識に失敗しました。リトライしてください。")

        # 描画を更新
        pygame.display.update()


    # rival selects a random move to attack with
    if game_status == 'rival turn':

        # check if the rival's pokemon fainted
        if rival_pokemon.current_hp == 0:
            game_status = 'fainted'
        else:
            game.fill(white)
            player_pokemon.draw()
            rival_pokemon.draw()
            player_pokemon.draw_hp()
            rival_pokemon.draw_hp()

            # empty the display box and pause for 2 seconds before attacking
            display_message('')
            waitFor(2000)

            # select a random move
            move = random.choice(rival_pokemon.moves)
            rival_pokemon.perform_attack(player_pokemon, move)

        # check if the player's pokemon fainted
        if player_pokemon.current_hp == 0 and (player_pokemon.name == "Charmander"):
            game.fill(white)
            player_pokemon.draw()
            rival_pokemon.draw()
            player_pokemon.draw_hp()
            rival_pokemon.draw_hp()
            pygame.display.update()
            waitFor(4000)
            game_status = 'evolution'
        elif player_pokemon.current_hp == 0 or rival_pokemon.current_hp == 0:
            game_status = 'fainted'
        else:
            game_status = 'player turn'
        pygame.display.update()

    if game_status == 'evolution':
        # フェードアウトと白い点滅演出
        alpha = 0
        while alpha < 255:
            game.fill(white)  # 画面を白く塗りつぶす
            rival_pokemon.draw()
            rival_pokemon.draw_hp()
            player_pokemon.draw(alpha=255 - alpha)  # 徐々に透明にする
            pygame.display.update()
            alpha += .4

        game.fill(white)
        display_message("おや？ ヒトカゲのようすが・・・？？？")
        waitFor(2000)  # メッセージ表示待機

        charmander = player_pokemon

        level = 99
        player_pokemon = Pokemon('Charizard', level, -40, 120)
        player_pokemon.set_moves()
        player_pokemon.current_hp = 1
        player_pokemon.size = 320
        player_pokemon.set_sprite('back_default')
        player_pokemon.hp_x = 275
        player_pokemon.hp_y = 250

        show_charmander = True
        alpha = 0
        while alpha < 255:
            game.fill(white)
            if show_charmander:
                charmander.draw(alpha=255 - alpha)
            else:
                player_pokemon.draw(alpha=alpha)
            show_charmander = not show_charmander
            rival_pokemon.draw()
            rival_pokemon.draw_hp()
            # player_pokemon.draw_hp()
            pygame.display.update()
            alpha += 1

        player_pokemon.draw()
        rival_pokemon.draw()
        player_pokemon.draw_hp()
        rival_pokemon.draw_hp()
        pygame.display.update()

        display_message("ヒトカゲは　リザードンに　しんかした！")
        waitFor(3000)

        player_pokemon.perform_attack(rival_pokemon, player_pokemon.moves[0])
        waitFor(1000)
        if rival_pokemon.current_hp == 0:
            game_status = 'fainted'

    # one of the pokemons fainted
    if game_status == 'fainted':

        alpha = 255
        while alpha > 0:

            game.fill(white)
            player_pokemon.draw_hp()
            rival_pokemon.draw_hp()

            # determine which pokemon fainted
            if rival_pokemon.current_hp == 0:
                player_pokemon.draw()
                rival_pokemon.draw(alpha)
                if rival_pokemon.name == 'Bulbasaur':
                    display_message("てきの　フシギダネ　は　たおれた！")
                elif rival_pokemon.name == 'Charmander':
                    display_message("てきの　ヒトカゲ　は　たおれた！")
                elif rival_pokemon.name == 'Squirtle':
                    display_message("てきの　ゼニガメ　は　たおれた！")
            else:
                player_pokemon.draw(alpha)
                rival_pokemon.draw()
                if player_pokemon.name == 'Bulbasaur':
                    display_message("フシギダネ　は　たおれた！")
                elif player_pokemon.name == 'Charmander':
                    display_message("ヒトカゲ　は　たおれた！")
                elif player_pokemon.name == 'Squirtle':
                    display_message("ゼニガメ　は　たおれた！")
            alpha -= .4

            pygame.display.update()

        game_status = 'gameover'

    # gameover screen
    if game_status == 'gameover':
        if is_battle_music_playing:
            pygame.mixer.music.stop()
            is_battle_music_playing = False
            pygame.mixer.music.load(win_sound)
            pygame.mixer.music.play(0)

        display_message('もういちど　たたかいますか？ (Y/N)?')

pygame.quit()
