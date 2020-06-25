import tcod, math, textwrap

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 80
MAP_HEIGHT = 43
LIMITFPS = 20
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10
MAX_ROOM_ENEMIES = 3
MAX_ROOM_ITEMS = 2
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT-PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
HEAL_AMOUNT = 4

class Tile:
    def __init__(self, blocked, blockSight = None):
        self.blocked = blocked
        self.explored = False
        if blockSight is None:
            blockSight = blocked
        self.blockSight = blockSight


class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        centerX = (self.x1 + self.x2) / 2
        centerY = (self.y1 + self.y2) / 2
        return centerX, centerY

    def intersect(self, other):
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y1 and self.y2 >= other.y2


class Object:

    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self


    def move(self, dx, dy):
        if not isBlocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def moveTowards(self, targetX, targetY):
        dx = targetX - self.x
        dy = targetY - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distanceTo(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def sendToBack(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def draw(self):
        if tcod.map_is_in_fov(fovMap, self.x, self.y):
            tcod.console_set_default_foreground(con, self.color)
            tcod.console_put_char(con, self.x, self.y, self.char, tcod.BKGND_NONE)

    def clear(self):
        tcod.console_put_char(con, self.x, self.y, ' ', tcod.BKGND_NONE)


class Fighter:
    def __init__(self, hp, defense, power, deathFunction=None):
        self.maxHp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.deathFunction = deathFunction

    def takeDamage(self, damage):
        if damage > 0:
            self.hp -= damage
        if self.hp <= 0:
            function = self.deathFunction
            if function is not None:
                function(self.owner)

    def attack(self, target):
        damage = self.power - target.fighter.defense
        if damage > 0:
            messages(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.takeDamage(damage)
        else:
            messages(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def heal(self, healAmount):
        self.hp += healAmount
        if self.hp > self.maxHp:
            self.hp = self.maxHp

class BasicEnemy:
    def takeTurn(self):
        #print 'The ' + self.owner.name + ' growls!'
        enemy = self.owner
        if tcod.map_is_in_fov(fovMap, enemy.x, enemy.y):
            if enemy.distanceTo(player) >= 2:
                enemy.moveTowards(player.x, player.y)
            elif player.fighter.hp > 0:
                enemy.fighter.attack(player)


class Item:

    def __init__(self, useFunction=None):
        self.useFunction = useFunction

    def pickup(self):
        if len(inventory) >= 26:
            messages('Your inventory is FULL!, cannot pick up' + self.owner.name + '.', tcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            messages('You picked up a ' + self.owner.name + '!', tcod.green)

    def use(self):
        if self.useFunction is None:
            messages('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.useFunction() != 'cancelled':
                inventory.remove(self.owner)


def isBlocked(x, y):
    if map[x][y].blocked:
        return True
    for object in objects:
        if object.blocks and object.x ==x and object.y == y:
            return True

def createRoom(room):
    global map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].blockSight = False


def createHTunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].blockSight = False


def createVTunnel(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].blockSight = False

def playerMoveOrAttack(dx, dy):
    global fovRecompute
    x = player.x + dx
    y = player.y + dy

    target = None
    for object in objects:
        if  object.fighter and object.x == x and object.y == y:
            target = object
            break
    if target is not None:
        player.fighter.attack(target)
    else:
         player.move(dx, dy)
         fovRecompute = True


def handleKeys():
    global fovRecompute, key
    #options
    if key.vk == tcod.KEY_ENTER and key.lalt:
        tcod.console_set_fullscreen(not tcod.console_is_fullscreen())
    elif key.vk == tcod.KEY_ESCAPE:
        return 'exit'

    #movement
    if gameState == 'playing':
        if key.vk == tcod.KEY_UP:
            playerMoveOrAttack(0, -1)
        elif key.vk == tcod.KEY_DOWN:
            playerMoveOrAttack(0, 1)
        elif key.vk == tcod.KEY_LEFT:
            playerMoveOrAttack(-1, 0)
        elif key.vk == tcod.KEY_RIGHT:
            playerMoveOrAttack(1, 0)
        else:
            keyChar = chr(key.c)
            if keyChar == 'g':
                for object in objects:
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pickup()
                        break
            if keyChar == 'i':
                chosenItem = inventoryMenu('Press the key next to an item to use it, or any other to cancel. \n')
                if chosenItem is not None:
                    chosenItem.use()
            return 'didnt-take-turn'


def makeMap():
    global map, player
    rooms = []
    numRooms = 0

    map = [[ Tile(True)
             for y in range(MAP_HEIGHT) ]
                for x in range(MAP_WIDTH) ]
    #creating random rooms
    for i in range(MAX_ROOMS):
        w = tcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = tcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        x = tcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = tcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
        newRoom = Rect(x, y, w, h)
        failed = False
        for otherRoom in rooms:
            if newRoom.intersect(otherRoom):
                failed = True
                break
        if not failed:
            createRoom(newRoom)
            newX, newY = newRoom.center()
            if numRooms == 0:
                 player.x = newX
                 player.y = newY
            else:
                prevX, prevY = rooms[numRooms - 1].center()
                if tcod.random_get_int(0, 0, 1) == 1:
                    createHTunnel(prevX, newX, prevY)
                    createVTunnel(prevY, newY, newX)
                else:
                    createVTunnel(prevY, newY, prevX)
                    createHTunnel(prevX, newX, newY)
            place_objects(newRoom)
            rooms.append(newRoom)
            numRooms += 1


def renderAll():
    global fovRecompute, fovMap
    if fovRecompute:
        fovRecompute = False
        tcod.map_compute_fov(fovMap, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visable = tcod.map_is_in_fov(fovMap, x, y)
            wall = map[x][y].blockSight
            if not visable:
                if map[x][y].explored:
                    if wall:
                        tcod.console_set_char_background(con, x, y, colorDarkWall, tcod.BKGND_SET)
                    else:
                        tcod.console_set_char_background(con, x, y, colorDarkGround, tcod.BKGND_SET)
            else:
                if wall:
                    tcod.console_set_char_background(con, x, y, colorLightWall, tcod.BKGND_SET)
                else:
                    tcod.console_set_char_background(con, x, y, colorLightGround, tcod.BKGND_SET)
                    map[x][y].explored = True
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    tcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    tcod.console_set_default_background(panel, tcod.black)
    tcod.console_clear(panel)
    tcod.console_set_default_foreground(panel, tcod.light_gray)
    tcod.console_print_ex(panel, 1, 0, tcod.BKGND_NONE, tcod.LEFT, getNamesUnderMouse())

#messageLog
    y = 1
    for (line, color) in gameMSGs:
        tcod.console_set_default_foreground(panel, color)
        tcod.console_print_ex(panel, MSG_X, y, tcod.BKGND_NONE,tcod.LEFT, line)
        y += 1
#health bar
    renderBar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.maxHp, tcod.light_red, tcod.darker_red)
    tcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def renderBar(x, y, totalWidth, name, value, max, barColor, backColor):
    barWidth = int(float(value) / max * totalWidth)
    tcod.console_set_default_foreground(panel, backColor)
    tcod.console_rect(panel, x, y, totalWidth, 1, False, tcod.BKGND_SCREEN)
    tcod.console_set_default_background(panel, barColor)
    if barWidth > 0:
        tcod.console_rect(panel, x, y, barWidth, 1, False, tcod.BKGND_SCREEN)
    tcod.console_set_default_foreground(panel, tcod.white)
    tcod.console_print_ex(panel, x + totalWidth / 2, y, tcod.BKGND_NONE, tcod.CENTER, name + ': ' + str(value) + '/' + str(max))

def place_objects(room):

#item loop
    numItems = tcod.random_get_int(0, 0, MAX_ROOM_ITEMS)
    for i in range(numItems):
        x = tcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = tcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
        if not isBlocked(x, y):
            itemComponent = Item(useFunction=castHeal)
            item = Object(x, y, '!', 'healing potion', tcod.violet, item=itemComponent)
            objects.append(item)
            item.sendToBack()

    numEnemies = tcod.random_get_int(0, 0, MAX_ROOM_ENEMIES)
#enemy loop
    for i in range(numEnemies):
        x = tcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = tcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not isBlocked(x, y):
            if tcod.random_get_int(0, 0, 100,) < 80:
                #ORC
                orcFighterComponent = Fighter(hp=5, defense=3, power=5, deathFunction=enemyDeath)
                aiComponent = BasicEnemy()
                enemy = Object(x, y, 'O', 'Orc', tcod.desaturated_green, blocks=True, fighter=orcFighterComponent, ai=aiComponent)
            else:
                #TROLL
                trollFighterComponent = Fighter(hp=8, defense=5, power=4, deathFunction=enemyDeath)
                aiComponent = BasicEnemy()
                enemy = Object(x, y, 'T', 'Troll', tcod.darker_green, blocks=True, fighter=trollFighterComponent, ai=aiComponent)
            objects.append(enemy)

def playerDeath(player):
    global gameState
    messages('YOU DIED!', tcod.darkest_red)
    gameState = 'dead'
    player.char = '%'
    player.color = tcod.darkest_red

def enemyDeath(enemy):
    messages(enemy.name.capitalize() + ' is dead!', tcod.orange)
    enemy.char = '%'
    enemy.color = tcod.darker_red
    enemy.blocks = False
    enemy.fighter = None
    enemy.ai = None
    enemy.name = 'remains of ' + enemy.name
    enemy.sendToBack()

def messages(newMessage, color=tcod.white):
    newMessageLines = textwrap.wrap(newMessage, MSG_WIDTH)
    for line in newMessageLines:
        if len(gameMSGs) == MSG_HEIGHT:
            del gameMSGs[0]
        gameMSGs.append((line, color))

def getNamesUnderMouse():
    global mouse
    (x, y) = (mouse.cx, mouse.cy)
    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and tcod.map_is_in_fov(fovMap, obj.x, obj.y)]
    names = ', '.join(names)
    return names.capitalize()

#remove letter from empty inventory
def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
    headerHeight = tcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + headerHeight
    window = tcod.console_new(width, height)
    tcod.console_set_default_foreground(window, tcod.white)
    tcod.console_print_rect_ex(window, 0, 0, width, height, tcod.BKGND_NONE, tcod.LEFT, header)
    y = headerHeight
    letterIndex = ord('a')
    for optionText in options:
        text = '(' + chr(letterIndex) + ') ' + optionText
        tcod.console_print_ex(window, 0, y, tcod.BKGND_NONE, tcod.LEFT, text)
        y += 1
        letterIndex += 1
    x = SCREEN_WIDTH / 2 - width / 2
    y = SCREEN_HEIGHT /2 - height / 2
    tcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
    tcod.console_flush()
    key = tcod.console_wait_for_keypress(True)

    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventoryMenu(header):
    if len(inventory) == 0:
        options = ['Inventory empty!']
    else:
        options = [item.name for item in inventory]
    index = menu(header, options, INVENTORY_WIDTH)
    if index is None or len(inventory) == 0:
        return None
    return inventory[index].item

def castHeal():
    if player.fighter.hp == player.fighter.maxHp:
        messages('You are already at full health!', tcod.red)
        return 'cancelled'
    messages('Your wounds start to feel better', tcod.lightest_cyan)
    player.fighter.heal(HEAL_AMOUNT)

#setup console
tcod.console_set_custom_font('arial10x10.png', tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD)
tcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/RogueGame', False)
con = tcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
tcod.sys_set_fps(LIMITFPS)

#basic classes
playerFighterComponent = Fighter(hp=123, defense=3, power=8, deathFunction=playerDeath)

#characters
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', tcod.turquoise, blocks=True, fighter=playerFighterComponent)
objects = [player]
inventory = []

#map colors
colorLightWall = tcod.Color(130,110,50)
colorLightGround = tcod.Color(200,1080,50)
colorDarkWall = tcod.Color(0, 0, 100)
colorDarkGround = tcod.Color(50, 50, 150)

#turns
gameState = 'playing'
playerAction = None
makeMap()

#field of view
fovMap = tcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        tcod.map_set_properties(fovMap, x, y, not map[x][y].blockSight, not map[x][y].blocked)

fovRecompute = True

#stat bars
panel = tcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

#game messages
gameMSGs = []
messages('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.')

#inputs
mouse = tcod.Mouse()
key = tcod.Key()

#main loop
while not tcod.console_is_window_closed():
    tcod.sys_check_for_event(tcod.EVENT_KEY_PRESS|tcod.EVENT_MOUSE_PRESS,key,mouse)
    renderAll()

    tcod.console_flush()

    for object in objects:
        object.clear()

    playerAction = handleKeys()
    if playerAction == 'exit':
        break
    if gameState == 'playing' and playerAction != 'didnt-take-turn':
        for object in objects:
            if object.ai:
                object.ai.takeTurn()