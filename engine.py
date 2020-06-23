import tcod

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 80
MAP_HEIGHT = 50
LIMITFPS = 20
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30



class Object:

    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color

    def move(self, dx, dy):
        if not map[self.x + dx][self.y + dy].blocked:
            self.x += dx
            self.y += dy

    def draw(self):
        tcod.console_set_default_foreground(con, self.color)
        tcod.console_put_char(con, self.x, self.y, self.char, tcod.BKGND_NONE)

    def clear(self):
        tcod.console_put_char(con, self.x, self.y, ' ', tcod.BKGND_NONE)


class Tile:
    def __init__(self, blocked, blockSight = None):
        self.blocked = blocked

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

def handleKeys():
    global player
    #options
    key = tcod.console_check_for_keypress(True)
    if key.vk == tcod.KEY_ENTER and key.lalt:
        tcod.console_set_fullscreen(not tcod.console_is_fullscreen())
    elif key.vk == tcod.KEY_ESCAPE:
        return True

    #movement
    if tcod.console_is_key_pressed(tcod.KEY_UP):
        player.move(0, -1)
    elif tcod.console_is_key_pressed(tcod.KEY_DOWN):
        player.move(0, 1)
    elif tcod.console_is_key_pressed(tcod.KEY_LEFT):
        player.move(-1, 0)
    elif tcod.console_is_key_pressed(tcod.KEY_RIGHT):
        player.move(1, 0)


def makeMap():
    global map, player
    rooms = []
    numRooms = 0

    map = [[ Tile(True)
             for y in range(MAP_HEIGHT) ]
                for x in range(MAP_WIDTH) ]
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
            rooms.append(newRoom)
            numRooms += 1


def renderAll():
    for object in objects:
        object.draw()
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            wall = map[x][y].blockSight
            if wall:
                tcod.console_set_char_background(con, x, y, colorDarkWall, tcod.BKGND_SET)
            else:
                tcod.console_set_char_background(con, x, y, colorDarGround, tcod.BKGND_SET)
    for object in objects:
        object.draw()

    tcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)


tcod.console_set_custom_font('arial10x10.png', tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD)
tcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/RogueGame', False)
con = tcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
tcod.sys_set_fps(LIMITFPS)
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', tcod.turquoise)
npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2 - 5, '*', tcod.red)
objects = [player, npc]
colorDarkWall = tcod.Color(0, 0, 100)
colorDarGround = tcod.Color(50, 50, 150)

makeMap()
while not tcod.console_is_window_closed():
    renderAll()

    tcod.console_flush()

    for object in objects:
        object.clear()

    exit = handleKeys()
    if exit:
        break
