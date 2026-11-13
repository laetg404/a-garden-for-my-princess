import math
import random
import time
import tkinter
import turtle

# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

WIDTH = 1100
HEIGHT = 760

FPS = 30
FRAME_MS = int(1000 / FPS)

WIND_STRENGTH = 1.0           # Intensidad del viento (1.0 = normal)
TULIP_ROWS = 4                # Filas de tulipanes (más filas = más profundidad)
TULIP_COLUMNS = 9             # Tulipanes por fila
                              # Si va lento, baja filas/columnas o FPS.

MESSAGE_DURATIONS = [30, 15, 0]   # Segundos por mensaje (0 = se queda para siempre)
FADE_SECONDS = 1.2                # Duración del fundido de cada mensaje

# Geometría del panel de texto (centrado en x = 0).
PANEL_HALF_WIDTH = 500
PANEL_TOP = -186
PANEL_BOTTOM = -372

# Altura donde empieza el campo de flores.
GROUND_TOP = -48

FONT_NAME = "Georgia"

TULIP_COLORS = [
    "#FF5277",  # Rosa
    "#FF8C42",  # Naranja
    "#FFE066",  # Amarillo
    "#B98AFF",  # Lila
    "#FF4F9A",  # Rosa intenso
    "#F4F0FF",  # Blanco
    "#FF4444",  # Rojo
    "#65D6A6",  # Verde menta
    "#79AFFF",  # Azul
    "#F7A6C8",  # Rosa pastel
]

STEM_GREEN = "#3F9467"
LEAF_GREEN = "#58B081"
HAZE = "#2C4468"              # Color de "neblina" para alejar las flores del fondo

PANEL_COLOR = "#0F1836"
PANEL_BORDER = "#5C4A8C"

# Gradiente del cielo: (posición 0..1, color).
SKY_TOP = 400
SKY_HORIZON = 20
SKY_STOPS = [
    (0.0, "#070A22"),
    (0.5, "#161B4C"),
    (1.0, "#5E3A7C"),
]

MOON_X, MOON_Y, MOON_R = 390, 255, 44


# ============================================================
# 2. UTILIDADES DE COLOR Y GEOMETRÍA
# ============================================================

def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(
        max(0, min(255, int(round(v)))) for v in rgb
    )


def mix(color_a, color_b, amount):
    # Mezcla dos colores (amount = 0 -> a, amount = 1 -> b).
    a = hex_to_rgb(color_a)
    b = hex_to_rgb(color_b)
    return rgb_to_hex([a[i] + (b[i] - a[i]) * amount for i in range(3)])


def darken(color, amount):
    return mix(color, "#000000", amount)


def lighten(color, amount):
    return mix(color, "#FFFFFF", amount)


def sky_color(y):
    t = max(0.0, min(1.0, (SKY_TOP - y) / (SKY_TOP - SKY_HORIZON)))

    for (t0, c0), (t1, c1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))

    return SKY_STOPS[-1][1]


def smooth(points, iterations=1):
    # Suavizado de polígonos cerrados (algoritmo de Chaikin).
    for _ in range(iterations):
        result = []
        count = len(points)

        for i in range(count):
            p = points[i]
            q = points[(i + 1) % count]
            result.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            result.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))

        points = result

    return points


def rounded_rect(x1, y1, x2, y2, radius, steps=6):
    points = []
    corners = [
        (x2 - radius, y2 - radius, 0),
        (x1 + radius, y2 - radius, 90),
        (x1 + radius, y1 + radius, 180),
        (x2 - radius, y1 + radius, 270),
    ]

    for cx, cy, start in corners:
        for i in range(steps + 1):
            angle = math.radians(start + 90 * i / steps)
            points.append((cx + math.cos(angle) * radius,
                           cy + math.sin(angle) * radius))

    return points


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


# Corazón unitario (se escala al dibujarlo).
HEART_UNIT = []
for _i in range(20):
    _t = _i * math.tau / 20
    HEART_UNIT.append((
        math.sin(_t) ** 3,
        (13 * math.cos(_t) - 5 * math.cos(2 * _t)
         - 2 * math.cos(3 * _t) - math.cos(4 * _t)) / 16
    ))


# ============================================================
# 3. CONFIGURACIÓN DE LA PANTALLA
# ============================================================

screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("A garden for my princess ♡")
screen.bgcolor(SKY_STOPS[0][1])
screen.tracer(0)

# Una tortuga por capa (el orden de creación define qué queda encima).
background = turtle.Turtle()
flowers = turtle.Turtle()
sparkles = turtle.Turtle()
ui = turtle.Turtle()

for pen in [background, flowers, sparkles, ui]:
    pen.speed(0)
    pen.hideturtle()
    pen.penup()


# ============================================================
# 4. PRIMITIVAS DE DIBUJO
# ============================================================

def polygon(pen, points, color):
    pen.penup()
    pen.goto(points[0])
    pen.color(color)
    pen.begin_fill()

    for point in points[1:]:
        pen.goto(point)

    pen.end_fill()


def circle(pen, x, y, radius, color, steps=None):
    pen.penup()
    pen.goto(x, y - radius)
    pen.color(color)
    pen.begin_fill()
    pen.circle(radius, steps=steps)
    pen.end_fill()


def line(pen, points, color, width=2):
    pen.penup()
    pen.goto(points[0])
    pen.pencolor(color)
    pen.pensize(width)
    pen.pendown()

    for point in points[1:]:
        pen.goto(point)

    pen.penup()


def sparkle_star(pen, x, y, radius, color):
    # Estrella de 4 puntas (cóncava).
    k = radius * 0.22
    polygon(pen, [
        (x, y + radius), (x + k, y + k),
        (x + radius, y), (x + k, y - k),
        (x, y - radius), (x - k, y - k),
        (x - radius, y), (x - k, y + k),
    ], color)


def heart(pen, x, y, size, color):
    polygon(pen, [(x + px * size, y + py * size) for px, py in HEART_UNIT], color)


# ============================================================
# 5. FONDO: CIELO, LUNA, MONTAÑAS Y CAMPO
# ============================================================

def mountains(x):
    return 35 + 40 * (1 - abs(math.sin(x * 0.0065 + 0.8))) + 8 * math.sin(x * 0.03)


def far_hills(x):
    return 5 + 24 * math.sin(x * 0.006 + 3.0) + 10 * math.sin(x * 0.017)


def mid_hills(x):
    return -22 + 14 * math.sin(x * 0.009 + 0.5) + 6 * math.sin(x * 0.03)


def field(x):
    return GROUND_TOP + 5 * math.sin(x * 0.011) + 3 * math.sin(x * 0.04 + 1)


def draw_hill(pen, func, color):
    points = [(x, func(x)) for x in range(-580, 601, 20)]
    points += [(600, -400), (-580, -400)]
    polygon(pen, points, color)


def draw_pine(pen, x, y, height, color):
    # Pino de tres niveles.
    for tier in range(3):
        base = y + height * tier * 0.28
        width = height * (0.32 - tier * 0.07)
        polygon(pen, [
            (x - width, base),
            (x, base + height * 0.46),
            (x + width, base),
        ], color)

    polygon(pen, [(x - 2, y - 4), (x - 2, y + 2), (x + 2, y + 2), (x + 2, y - 4)], color)


def draw_sky():
    # Gradiente construido con franjas horizontales.
    for y in range(SKY_TOP, -60, -10):
        polygon(background, [
            (-580, y), (580, y), (580, y - 11), (-580, y - 11)
        ], sky_color(y - 5))


def draw_moon():
    # Resplandor suave alrededor de la luna.
    for i in range(7, 0, -1):
        radius = MOON_R + i * 9
        glow = mix(sky_color(MOON_Y), "#FFE9A8", 0.03 * (8 - i))
        circle(background, MOON_X, MOON_Y, radius, glow, steps=48)

    circle(background, MOON_X, MOON_Y, MOON_R, "#FFF1C1")

    # Cráteres.
    for dx, dy, r in [(-14, 10, 9), (16, -12, 7), (4, 22, 5), (-20, -18, 5), (22, 14, 4)]:
        circle(background, MOON_X + dx, MOON_Y + dy, r, "#F3DFA2", steps=18)


def draw_static_stars():
    for _ in range(140):
        x = random.randint(-540, 540)
        y = random.randint(40, 390)

        # Evitar el resplandor de la luna.
        if math.hypot(x - MOON_X, y - MOON_Y) < 105:
            continue

        radius = random.uniform(0.8, 2.6)
        color = random.choice(["#FFFFFF", "#FFF1BD", "#C5D7FF", "#E8D5FF"])
        # Las estrellas cercanas al horizonte se ven más tenues.
        fade = max(0.0, (60 - y) / 120) + 0.05
        circle(background, x, y, radius, mix(color, sky_color(y), fade), steps=8)


def draw_grass():
    colors = ["#1F5A4B", "#2A6B52", "#194A41", "#2F7A58"]

    for _ in range(340):
        x = random.uniform(-570, 570)
        y = random.uniform(-182, GROUND_TOP - 6)
        depth = max(0.0, min(1.0, (GROUND_TOP - y) / 134))

        height = random.uniform(8, 20) * (0.45 + depth)
        width = 1.5 + depth * 2.2
        lean = random.uniform(-5, 5)

        color = mix(random.choice(colors), HAZE, (1 - depth) * 0.35)
        polygon(background, [(x - width, y), (x + lean, y + height), (x + width, y)], color)


def draw_background():
    random.seed(25)   # Paisaje siempre igual (estrellas, pinos, hierba)

    draw_sky()
    draw_static_stars()
    draw_moon()

    # Montañas lejanas.
    draw_hill(background, mountains, "#322E69")

    # Colinas con pinos.
    draw_hill(background, far_hills, "#262C5E")

    for _ in range(11):
        x = random.randint(-540, 540)
        draw_pine(background, x, far_hills(x) - 3, random.randint(34, 56), "#1B2457")

    draw_hill(background, mid_hills, "#1D3B58")

    # Campo lejano de flores diminutas sobre la colina.
    for _ in range(160):
        x = random.uniform(-570, 570)
        y = mid_hills(x) - random.uniform(2, 16)
        color = mix(random.choice(TULIP_COLORS), "#1D3B58", 0.55)
        circle(background, x, y, random.uniform(1.0, 2.0), color, steps=6)

    # Campo principal con degradado hacia abajo.
    draw_hill(background, field, "#1A4E46")
    draw_hill(background, lambda x: field(x) - 45, "#17433F")
    draw_hill(background, lambda x: field(x) - 105, "#133A37")

    draw_grass()

    random.seed()


# ============================================================
# 6. TULIPANES
# ============================================================

# Formas del tulipán (coordenadas locales, la base de la flor es (0, 0)).
BACK_PETAL_LEFT = [(-2, 4), (-13, 20), (-15, 44), (-10, 64), (-2, 44)]
BACK_PETAL_RIGHT = [(-x, y) for x, y in BACK_PETAL_LEFT]

CUP = smooth([
    (0, 0), (-13, 3), (-22, 15), (-25, 34), (-19, 52), (-10, 60),
    (0, 46), (10, 60), (19, 52), (25, 34), (22, 15), (13, 3),
])

CENTER_PETAL = smooth([
    (-8, 3), (-14, 22), (-11, 44), (0, 66), (11, 44), (14, 22), (8, 3), (0, 0),
])

HIGHLIGHT = [(-3, 8), (-6, 28), (-2, 50), (2, 50), (4, 28), (2, 8)]


def create_tulips():
    tulips = []
    spacing = WIDTH / TULIP_COLUMNS

    for row in range(TULIP_ROWS):
        # row = 0 es la fila más lejana, la última es la más cercana.
        depth = row / max(1, TULIP_ROWS - 1)
        row_y = -66 + (-172 + 66) * depth

        for column in range(TULIP_COLUMNS):
            offset = spacing * 0.5 if row % 2 else 0
            x = -WIDTH / 2 + spacing * (column + 0.5) + offset
            x += random.uniform(-28, 28)
            x = max(-535, min(535, x))

            base_y = row_y + random.uniform(-8, 8)
            scale = (0.62 + 0.6 * depth) * random.uniform(0.88, 1.12)
            height = random.uniform(115, 175) * scale

            # Las flores lejanas se mezclan con la neblina.
            haze = (1 - depth) * 0.5
            color = mix(random.choice(TULIP_COLORS), HAZE, haze)
            leaf_light = mix(LEAF_GREEN, HAZE, haze)

            tulips.append({
                "x": x,
                "base_y": base_y,
                "height": height,
                "scale": scale,
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.7, 1.4),
                "amplitude": random.uniform(4, 11),
                "palette": {
                    "back": darken(color, 0.42),
                    "shade": darken(color, 0.25),
                    "base": color,
                    "light": lighten(color, 0.38),
                    "stem": mix(STEM_GREEN, HAZE, haze),
                    "leaf_light": leaf_light,
                    "leaf_dark": darken(leaf_light, 0.25),
                },
            })

    # Primero se dibujan las flores lejanas (base_y más alta).
    tulips.sort(key=lambda t: t["base_y"], reverse=True)
    return tulips


def draw_leaf(pen, x, y, angle, length, width, bend, palette):
    # Hoja larga y curvada, dividida en dos mitades para dar volumen.
    steps = 4
    segment = length / steps

    mids = [(x, y)]
    lefts = [(x, y)]
    rights = [(x, y)]
    px, py = x, y

    for i in range(1, steps + 1):
        a = angle + bend * (i / steps)
        px += math.cos(a) * segment
        py += math.sin(a) * segment
        w = width * max(0.0, math.sin(math.pi * i / steps)) ** 0.7
        nx, ny = -math.sin(a), math.cos(a)

        mids.append((px, py))
        lefts.append((px + nx * w, py + ny * w))
        rights.append((px - nx * w, py - ny * w))

    polygon(pen, lefts + mids[::-1], palette["leaf_light"])
    polygon(pen, rights + mids[::-1], palette["leaf_dark"])


def place(points, cx, cy, scale, cos_a, sin_a):
    # Escala, rota y traslada una forma local al tallo.
    return [
        (cx + (px * cos_a - py * sin_a) * scale,
         cy + (px * sin_a + py * cos_a) * scale)
        for px, py in points
    ]


def draw_tulip(pen, tulip, t):
    x = tulip["x"]
    base_y = tulip["base_y"]
    height = tulip["height"]
    scale = tulip["scale"]
    palette = tulip["palette"]

    # Viento: ráfagas lentas + una onda que viaja por el campo.
    gust = 1.0 + 0.45 * math.sin(t * 0.35) + 0.25 * math.sin(t * 0.9 + 1.3)
    phase = t * tulip["speed"] + tulip["phase"] + x * 0.006
    sway = math.sin(phase) * tulip["amplitude"] * WIND_STRENGTH * gust

    # Hojas basales.
    leaf_sway = sway * 0.012
    leaf_width = 10 * scale
    draw_leaf(pen, x - 1, base_y, math.radians(70) + leaf_sway,
              height * 0.60, leaf_width, -0.9, palette)
    draw_leaf(pen, x + 1, base_y, math.radians(110) + leaf_sway,
              height * 0.54, leaf_width, 0.9, palette)

    # Tallo ligeramente curvo.
    stem = [
        (x + sway * (i / 6) ** 1.6, base_y + height * i / 6)
        for i in range(7)
    ]
    line(pen, stem, palette["stem"], max(2, round(4 * scale)))

    # La flor se inclina siguiendo la punta del tallo.
    cx, cy = stem[-1]
    tilt = -math.atan2(1.6 * sway, height)
    cos_a, sin_a = math.cos(tilt), math.sin(tilt)

    polygon(pen, place(BACK_PETAL_LEFT, cx, cy, scale, cos_a, sin_a), palette["back"])
    polygon(pen, place(BACK_PETAL_RIGHT, cx, cy, scale, cos_a, sin_a), palette["back"])
    polygon(pen, place(CUP, cx, cy, scale, cos_a, sin_a), palette["shade"])
    polygon(pen, place(CENTER_PETAL, cx, cy, scale, cos_a, sin_a), palette["base"])
    polygon(pen, place(HIGHLIGHT, cx, cy, scale, cos_a, sin_a), palette["light"])


# ============================================================
# 7. PARTÍCULAS: PÉTALOS, LUCIÉRNAGAS, ESTRELLAS Y CORAZONES
# ============================================================

petals = []
fireflies = []
twinkling_stars = []
floating_hearts = []
shooting_star = {"life": 0}


def create_petal(anywhere=False):
    return {
        "x": random.uniform(-520, 520),
        "y": random.uniform(-100, 380) if anywhere else 395,
        "speed": random.uniform(0.7, 1.6),
        "phase": random.uniform(0, math.tau),
        "spin": random.uniform(1.5, 3.5),
        "color": random.choice(TULIP_COLORS),
        "size": random.uniform(3, 5.5),
    }


def create_particles():
    for _ in range(12):
        petals.append(create_petal(anywhere=True))

    for _ in range(14):
        fireflies.append({
            "x": random.uniform(-500, 500),
            "y": random.uniform(-150, 60),
            "range": random.uniform(20, 55),
            "speed": random.uniform(0.3, 0.8),
            "pulse": random.uniform(1.5, 3.0),
            "phase": random.uniform(0, math.tau),
        })

    for _ in range(18):
        twinkling_stars.append({
            "x": random.uniform(-540, 540),
            "y": random.uniform(70, 385),
            "speed": random.uniform(1.0, 2.5),
            "phase": random.uniform(0, math.tau),
        })


def draw_twinkling_stars(pen, t):
    for star in twinkling_stars:
        if math.hypot(star["x"] - MOON_X, star["y"] - MOON_Y) < 100:
            continue

        glow = 0.5 + 0.5 * math.sin(t * star["speed"] + star["phase"])
        color = mix(sky_color(star["y"]), "#FFF7D6", 0.35 + 0.65 * glow)
        sparkle_star(pen, star["x"], star["y"], 1.5 + 4.5 * glow, color)


def update_shooting_star(pen):
    if shooting_star["life"] <= 0:
        # Aparece de vez en cuando.
        if random.random() < 0.003:
            shooting_star.update({
                "x": random.uniform(-250, 350),
                "y": random.uniform(230, 340),
                "vx": -random.uniform(11, 15),
                "vy": -random.uniform(4, 6),
                "life": 30,
            })
        return

    shooting_star["x"] += shooting_star["vx"]
    shooting_star["y"] += shooting_star["vy"]
    shooting_star["life"] -= 1

    x, y = shooting_star["x"], shooting_star["y"]
    vx, vy = shooting_star["vx"], shooting_star["vy"]

    # Cola con degradado.
    for k in range(5):
        x1, y1 = x - vx * k * 0.8, y - vy * k * 0.8
        x2, y2 = x - vx * (k + 1) * 0.8, y - vy * (k + 1) * 0.8
        line(pen, [(x1, y1), (x2, y2)],
             mix("#FFFFFF", sky_color(y), k / 5), max(1, 3 - k // 2))


def draw_fireflies(pen, t):
    for fly in fireflies:
        fx = fly["x"] + math.cos(t * fly["speed"] + fly["phase"]) * fly["range"] * 2
        fy = fly["y"] + math.sin(t * fly["speed"] * 1.3 + fly["phase"]) * fly["range"] * 0.6
        fy = max(-175, fy)

        pulse = 0.5 + 0.5 * math.sin(t * fly["pulse"] + fly["phase"])
        backdrop = "#1C3F40" if fy < -40 else "#27325F"

        circle(pen, fx, fy, 9, mix(backdrop, "#FFE98A", 0.08 + 0.14 * pulse), steps=10)
        circle(pen, fx, fy, 5, mix(backdrop, "#FFE98A", 0.25 + 0.30 * pulse), steps=10)
        circle(pen, fx, fy, 2, mix(backdrop, "#FFF8C8", 0.60 + 0.40 * pulse), steps=8)


def draw_falling_petals(pen, t):
    if len(petals) < 16 and random.random() < 0.04:
        petals.append(create_petal())

    for petal in petals[:]:
        petal["y"] -= petal["speed"]
        petal["x"] += 0.5 + math.sin(t * 1.5 + petal["phase"]) * 1.4

        if petal["y"] < -172 or petal["x"] > 570:
            petals.remove(petal)
            continue

        # El pétalo "gira" variando su ancho aparente.
        spin = t * petal["spin"] + petal["phase"]
        w = petal["size"] * abs(math.cos(spin)) + 0.8
        h = petal["size"] * 1.4
        tilt = math.sin(t + petal["phase"]) * 0.6
        ca, sa = math.cos(tilt), math.sin(tilt)

        shape = [(0, h), (w, 0), (0, -h), (-w, 0)]
        polygon(pen, [
            (petal["x"] + px * ca - py * sa, petal["y"] + px * sa + py * ca)
            for px, py in shape
        ], petal["color"])


def draw_floating_hearts(pen, t, active):
    # Corazones que suben durante el último mensaje.
    if active and len(floating_hearts) < 10 and random.random() < 0.05:
        floating_hearts.append({
            "x": random.uniform(-480, 480),
            "y": -172,
            "speed": random.uniform(0.8, 1.6),
            "phase": random.uniform(0, math.tau),
            "size": random.uniform(5, 10),
            "color": random.choice(["#FF6F9F", "#FF9EC4", "#FFB3D1", "#FF5277"]),
        })

    for item in floating_hearts[:]:
        item["y"] += item["speed"]
        item["x"] += math.sin(t * 1.2 + item["phase"]) * 0.8

        if item["y"] > 300:
            floating_hearts.remove(item)
            continue

        heart(pen, item["x"], item["y"], item["size"], item["color"])


def update_sparkles(t):
    sparkles.clear()

    draw_twinkling_stars(sparkles, t)
    update_shooting_star(sparkles)
    draw_fireflies(sparkles, t)
    draw_falling_petals(sparkles, t)
    draw_floating_hearts(sparkles, t, message_index == len(MESSAGES) - 1)


# ============================================================
# 8. MENSAJES Y PANEL DE TEXTO
# ============================================================

MESSAGES = [
    {
        "title": "Para mí princesa ♡",
        "body": (
            "Hoy el cielo tiene un motivo más para brillar,\n"
            "porque un día como hoy llegaste a este mundo.\n"
            "Y entre tantas casualidades de la vida,\n"
            "la mía más bonita fue encontrarte."
        )
    },
    {
        "title": "Mí amor...",
        "body": (
            "Si pudiera regalarte todas las flores del mundo,\n"
            "lo haría sin pensarlo, aunque ninguna sería\n"
            "tan hermosa como tú.\n"
            "Gracias por llenar mis días de tanto amor.\n"
            "Eres uno de mis lugares favoritos en el mundo."
        )
    },
    {
        "title": "¡Feliz cumpleaños, mí cielo! ♡",
        "body": (
            "Deseo que la vida te regale infinitas razones para sonreír, \n"
            "sueños que se hagan realidad y muchísimos momentos llenos de felicidad.\n"
            "Quiero seguir celebrando cada estación contigo,\n"
            "amándote un poquito más cada día.\n"
            "Te amo muchísimo. ♡"
        )
    }
]

TITLE_HEIGHT = 32
DIVIDER_GAP = 26
LINE_HEIGHT = 24

message_index = 0
message_started = time.time()
fade_complete = False


def draw_panel_background():
    # Borde exterior, relleno y una línea fina interior.
    polygon(ui, rounded_rect(-PANEL_HALF_WIDTH - 3, PANEL_BOTTOM - 3,
                             PANEL_HALF_WIDTH + 3, PANEL_TOP + 3, 22), PANEL_BORDER)
    polygon(ui, rounded_rect(-PANEL_HALF_WIDTH, PANEL_BOTTOM,
                             PANEL_HALF_WIDTH, PANEL_TOP, 20), PANEL_COLOR)

    inner = rounded_rect(-PANEL_HALF_WIDTH + 8, PANEL_BOTTOM + 8,
                         PANEL_HALF_WIDTH - 8, PANEL_TOP - 8, 14)
    line(ui, inner + [inner[0]], "#262F63", 1)


def draw_message(progress):
    # progress va de 0 a 1 y controla el fundido del texto.
    ease = smoothstep(progress)
    message = MESSAGES[message_index]
    lines = message["body"].split("\n")

    ui.clear()
    draw_panel_background()

    # El bloque de texto se centra verticalmente dentro del panel.
    block_height = TITLE_HEIGHT + DIVIDER_GAP + len(lines) * LINE_HEIGHT
    center_y = (PANEL_TOP + PANEL_BOTTOM) / 2 + 5
    top = center_y + block_height / 2

    # Título.
    ui.goto(0, top - TITLE_HEIGHT)
    ui.color(mix(PANEL_COLOR, "#FFD9EC", ease))
    ui.write(message["title"], align="center", font=(FONT_NAME, 21, "bold"))

    # Separador con corazón central.
    divider_y = top - TITLE_HEIGHT - 6
    divider_color = mix(PANEL_COLOR, "#8E78B8", ease)
    line(ui, [(-220, divider_y), (-22, divider_y)], divider_color, 2)
    line(ui, [(22, divider_y), (220, divider_y)], divider_color, 2)
    heart(ui, 0, divider_y, 7, mix(PANEL_COLOR, "#FF6F9F", ease))

    # Cuerpo: una línea a la vez, para controlar el interlineado.
    ui.color(mix(PANEL_COLOR, "#FFF5F8", ease))

    for i, text_line in enumerate(lines):
        y = top - TITLE_HEIGHT - DIVIDER_GAP - (i + 1) * LINE_HEIGHT + 3
        ui.goto(0, y)
        ui.write(text_line, align="center", font=(FONT_NAME, 12, "normal"))

    # Indicador de progreso (puntos) centrado abajo.
    for i in range(len(MESSAGES)):
        x = (i - (len(MESSAGES) - 1) / 2) * 16
        active = i == message_index
        circle(ui, x, PANEL_BOTTOM + 14, 3.2,
               mix(PANEL_COLOR, "#FFD9EC" if active else "#3C4272", ease), steps=10)

    # Pista de teclado (no aparece en el último mensaje).
    if message_index < len(MESSAGES) - 1:
        ui.goto(PANEL_HALF_WIDTH - 24, PANEL_BOTTOM + 8)
        ui.color(mix(PANEL_COLOR, "#8C8FBF", ease))
        ui.write("SPACE ▸", align="right", font=(FONT_NAME, 9, "normal"))


def next_message():
    global message_index, message_started, fade_complete

    if message_index < len(MESSAGES) - 1:
        message_index += 1
        message_started = time.time()
        fade_complete = False


def update_messages(now):
    global fade_complete

    elapsed = now - message_started

    # Fundido de entrada del mensaje actual.
    if not fade_complete:
        progress = elapsed / FADE_SECONDS
        draw_message(progress)
        fade_complete = progress >= 1

    # Avance automático.
    duration = MESSAGE_DURATIONS[message_index]

    if duration > 0 and elapsed >= duration:
        next_message()


# ============================================================
# 9. ANIMACIÓN PRINCIPAL
# ============================================================

START_TIME = time.time()


def animate():
    try:
        now = time.time()
        t = now - START_TIME

        flowers.clear()

        for tulip in tulips:
            draw_tulip(flowers, tulip, t)

        update_sparkles(t)
        update_messages(now)

        screen.update()
        screen.ontimer(animate, FRAME_MS)

    except (turtle.Terminator, tkinter.TclError):
        # La ventana se cerró: salir sin mostrar errores.
        pass


# ============================================================
# 10. INICIAR EL PROGRAMA
# ============================================================

draw_background()

tulips = create_tulips()
create_particles()

screen.listen()
screen.onkey(next_message, "space")

animate()

try:
    screen.mainloop()
except (turtle.Terminator, tkinter.TclError):
    pass