import tcod, math

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 80
MAP_HEIGHT = 50
LIMITFPS = 20
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10
MAX_ROOM_ENEMIES = 3

class Object:

    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
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
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.'
            target.fighter.takeDamage(damage)
        else:
            self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!'


class BasicEnemy:
    def takeTurn(self):
        #print 'The ' + self.owner.name + ' growls!'
        enemy = self.owner
        if tcod.map_is_in_fov(fovMap, enemy.x, enemy.y):
            if enemy.distanceTo(player) >= 2:
                enemy.moveTowards(player.x, player.y)
            elif player.fighter.hp > 0:
                enemy.fighter.attack(player)


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
    global fovRecompute
    #options
    key = tcod.console_check_for_keypress(True)
    if key.vk == tcod.KEY_ENTER and key.lalt:
        tcod.console_set_fullscreen(not tcod.console_is_fullscreen())
    elif key.vk == tcod.KEY_ESCAPE:
        return 'exit'

    #movement
    if gameState == 'playing':
        if tcod.console_is_key_pressed(tcod.KEY_UP):
            playerMoveOrAttack(0, -1)
        elif tcod.console_is_key_pressed(tcod.KEY_DOWN):
            playerMoveOrAttack(0, 1)
        elif tcod.console_is_key_pressed(tcod.KEY_LEFT):
            playerMoveOrAttack(-1, 0)
        elif tcod.console_is_key_pressed(tcod.KEY_RIGHT):
            playerMoveOrAttack(1, 0)
        else:
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
    tcod.console_set_default_foreground(con, tcod.white)
    tcod.console_print_ex(con, 1, SCREEN_HEIGHT - 2, tcod.BKGND_NONE, tcod.LEFT, 'HP: ' + str(player.fighter.hp) + '/' + str(player.fighter.maxHp))


def place_objects(room):
    numEnemies = tcod.random_get_int(0, 0, MAX_ROOM_ENEMIES)

    for i in range(numEnemies):
        x = tcod.random_get_int(0, room.x1, room.x2)
        y = tcod.random_get_int(0, room.y1, room.y2)

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
    print 'YOU DIED!'
    gameState = 'dead'
    player.char = '%'
    player.color = tcod.darkest_red

def enemyDeath(enemy):
    print enemy.name.capitalize() + ' is dead!'
    enemy.char = '%'
    enemy.color = tcod.darker_red
    enemy.blocks = False
    enemy.fighter = None
    enemy.ai = None
    enemy.name = 'remains of ' + enemy.name
    enemy.sendToBack()


tcod.console_set_custom_font('arial10x10.png', tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD)
tcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/RogueGame', False)
con = tcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
tcod.sys_set_fps(LIMITFPS)

#basic classes
playerFighterComponent = Fighter(hp=123, defense=3, power=8, deathFunction=playerDeath)

#characters
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', tcod.turquoise, blocks=True, fighter=playerFighterComponent)
objects = [player]

#map colors
colorLightWall = tcod.Color(130,110,50)
colorLightGround = tcod.Color(200,1080,50)
colorDarkWall = tcod.Color(0, 0, 100)
colorDarkGround = tcod.Color(50, 50, 150)

gameState = 'playing'
playerAction = None

makeMap()

fovMap = tcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        tcod.map_set_properties(fovMap, x, y, not map[x][y].blockSight, not map[x][y].blocked)

fovRecompute = True

while not tcod.console_is_window_closed():
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