import time
import math
import random
import network
import M5
import gc

try:
    from umqtt.simple import MQTTClient
    _HAS_MQTT = True
except ImportError:
    _HAS_MQTT = False

try:
    from hardware.stackchan import StackChan
    _HAS_STACKCHAN = True
except ImportError:
    _HAS_STACKCHAN = False

stars = 5                      
state = "sleeping"             

W, H = 320, 240
cx, cy = 160, 120
ip_addr = "offline"
R_STAR = 10

sc = None

# ---- Configurazione MQTT ----
MQTT_BROKER = "broker.hivemq.com"
CLIENT_ID = "festival-ai_bit-demo_" + str(random.randint(10000, 99999))
CMD_TOPIC = b"festival-ai/2026/bit-demo/cmd"
STATUS_TOPIC = b"festival-ai/2026/bit-demo/status"
mqtt_client = None
last_mqtt_reconnect = 0
ping_next = 0

# Paletta Colori Originale
BG_DARK = 0x0B0B1A
BG_ANGRY = 0xB71C1C
BG = BG_DARK
EYE_WHITE = 0xFFFFFF
PUPIL = 0x000000
MOUTH = 0xFFC107
BROW = 0xFFC107
DARK_FEATURE = 0x141414
TEXT = 0xBBBBBB
STAR = 0xFFD54F

# Geometria Faccia
EYE_DX = 55
EYE_R = 20
EYE_Y_OFF = 28
MOUTH_Y_OFF = 48
BROW_Y_OFF = 56
EDGE = EYE_DX + 28

# Limiti Sicuri Motori
X_MIN, X_MAX = -45.0, 45.0
Y_MIN, Y_MAX = 15.0, 70.0

# Stato Animazioni Faccia
pupil_dx, pupil_dy = 0, 0
blink_until, blink_next, pupil_next = 0, 0, 0
closed_side = 1             
mouth_open = False
mouth_next = 0

# Stato Motore Fisico (Architettura a Waypoint Sicuri)
servo_next = 0
current_x = 0.0
current_y = 40.0
servo_entered = False

# Stato LED, Memoria e Sirena
rgb_next = 0
rgb_on = False
gc_next = 0
siren_next = 0
siren_high = False


# ---- Helper Grafici ----
def _eye_y(): return cy - EYE_Y_OFF
def _mouth_y(): return cy + MOUTH_Y_OFF
def _brow_y(): return cy - BROW_Y_OFF

def _state_color(name):
    return {"sleeping": 0x0381FF, "waking_up": 0x00D7DB, "awake": 0x00DB00, "angry": 0xFF6F00}.get(name, TEXT)

def thick_line(x0, y0, x1, y1, w, color):
    for i in range(w): M5.Lcd.drawLine(x0, y0 + i, x1, y1 + i, color)

def _set_rgb(color):
    if sc:
        try: sc.set_rgb_color(color)
        except: pass


# ---- Gestione Stelle ----
def star_vertices(sx, sy, R, r):
    pts = []
    for i in range(5):
        a_o = math.radians(-90 + i * 72)
        a_i = math.radians(-90 + 36 + i * 72)
        pts.append((sx + R * math.cos(a_o), sy + R * math.sin(a_o)))
        pts.append((sx + r * math.cos(a_i), sy + r * math.sin(a_i)))
    return pts

def fill_star(sx, sy, R, color):
    pts = star_vertices(sx, sy, R, R * 0.42)
    outer = [pts[i] for i in range(0, 10, 2)]
    inner = [pts[i] for i in range(1, 10, 2)]
    for i in range(5):
        M5.Lcd.fillTriangle(int(outer[i][0]), int(outer[i][1]), int(inner[i - 1][0]), int(inner[i - 1][1]), int(inner[i][0]), int(inner[i][1]), color)
    for i in range(1, 4):
        M5.Lcd.fillTriangle(int(inner[0][0]), int(inner[0][1]), int(inner[i][0]), int(inner[i][1]), int(inner[i + 1][0]), int(inner[i + 1][1]), color)

def draw_star(sx, sy, R, color):
    pts = star_vertices(sx, sy, R, R * 0.42)
    for i in range(5):
        M5.Lcd.drawLine(int(pts[2*i][0]), int(pts[2*i][1]), int(pts[2*i+1][0]), int(pts[2*i+1][1]), color)
        M5.Lcd.drawLine(int(pts[2*i+1][0]), int(pts[2*i+1][1]), int(pts[(2*i+2)%10][0]), int(pts[(2*i+2)%10][1]), color)

def _draw_stars():
    M5.Lcd.fillRect(0, H - 2 * R_STAR - 8, W, 2 * R_STAR + 10, BG)
    gap = max(2, R_STAR // 3)
    x0 = cx - (10 * (2 * R_STAR) + 9 * gap) // 2
    for i in range(10):
        sx = x0 + i * (2 * R_STAR + gap) + R_STAR
        if i < stars: fill_star(sx, H - R_STAR - 6, R_STAR, STAR)
        else: draw_star(sx, H - R_STAR - 6, R_STAR, STAR)

def _draw_hud(label):
    # FIX: Pulisce la barra in alto prima di riscrivere per evitare sovrapposizioni
    M5.Lcd.fillRect(0, 0, W, 24, BG)
    M5.Lcd.setFont(M5.Lcd.FONTS.Montserrat16)
    M5.Lcd.setTextColor(TEXT, BG)
    M5.Lcd.setCursor(6, 4)
    # if mqtt_client:
        # M5.Lcd.print("MQTT: OK  ", TEXT)
    # else:
        # M5.Lcd.print("MQTT: ERR ", 0xFF0000)
    M5.Lcd.print(label, _state_color(label))
    _draw_stars()


# ---- Rendering Faccia ----
def _draw_face(name):
    M5.Lcd.fillScreen(BG)
    by = _brow_y()
    if name == "waking_up":
        thick_line(cx - EYE_DX - 22, by + 10, cx - EYE_DX + 22, by + 2, 5, BROW)
        thick_line(cx + EYE_DX - 22, by + 2, cx + EYE_DX + 22, by + 2, 5, BROW)
    elif name == "angry":
        thick_line(cx - EYE_DX - 24, by + 10, cx - EYE_DX + 24, by - 4, 6, DARK_FEATURE)
        thick_line(cx + EYE_DX + 24, by + 10, cx + EYE_DX - 24, by - 4, 6, DARK_FEATURE)

    for ex, side in ((cx - EYE_DX, -1), (cx + EYE_DX, 1)):
        mode = "closed"
        if name == "waking_up" and side != closed_side: mode = "awake"
        elif name == "awake": mode = "awake"
        elif name == "angry": mode = "angry"
        
        if mode == "closed": M5.Lcd.fillRect(ex - 22, _eye_y() - 3, 44, 6, EYE_WHITE)
        else:
            M5.Lcd.fillCircle(ex, _eye_y(), EYE_R, EYE_WHITE)
            M5.Lcd.fillCircle(ex + pupil_dx, _eye_y() + pupil_dy, EYE_R // (2 if mode=="awake" else 3), PUPIL)

    my = _mouth_y()
    if name == "sleeping":
        if mouth_open: M5.Lcd.fillCircle(cx, my + 2, 15, MOUTH)
        else: M5.Lcd.fillRect(cx - 10, my, 20, 4, MOUTH)
    elif name == "waking_up": M5.Lcd.fillCircle(cx, my + 4, 7, MOUTH)
    elif name == "awake":
        M5.Lcd.fillCircle(cx, my, 16, MOUTH)
        M5.Lcd.fillRect(cx - 18, my - 16, 36, 16, BG)
    elif name == "angry":
        M5.Lcd.fillCircle(cx, my, 16, DARK_FEATURE)
        M5.Lcd.fillRect(cx - 18, my, 36, 16, BG)

def _redraw_eyes(blink):
    M5.Lcd.fillRect(cx - EDGE, cy - BROW_Y_OFF - 10, EDGE * 2, BROW_Y_OFF + EYE_R + 4, BG)
    by = _brow_y()
    if state == "waking_up":
        thick_line(cx - EYE_DX - 22, by + 10, cx - EYE_DX + 22, by + 2, 5, BROW)
        thick_line(cx + EYE_DX - 22, by + 2, cx + EYE_DX + 22, by + 2, 5, BROW)
    elif state == "angry":
        thick_line(cx - EYE_DX - 24, by + 10, cx - EYE_DX + 24, by - 4, 6, DARK_FEATURE)
        thick_line(cx + EYE_DX + 24, by + 10, cx + EYE_DX - 24, by - 4, 6, DARK_FEATURE)

    for ex, side in ((cx - EYE_DX, -1), (cx + EYE_DX, 1)):
        mode = "closed"
        if not blink:
            if state == "waking_up" and side != closed_side: mode = "awake"
            elif state == "awake": mode = "awake"
            elif state == "angry": mode = "angry"
        
        if mode == "closed": M5.Lcd.fillRect(ex - 22, _eye_y() - 3, 44, 6, EYE_WHITE)
        else:
            M5.Lcd.fillCircle(ex, _eye_y(), EYE_R, EYE_WHITE)
            M5.Lcd.fillCircle(ex + pupil_dx, _eye_y() + pupil_dy, EYE_R // (2 if mode=="awake" else 3), PUPIL)

def _redraw_mouth():
    M5.Lcd.fillRect(cx - 18, _mouth_y() - 18, 36, 40, BG)
    my = _mouth_y()
    if state == "sleeping":
        if mouth_open: M5.Lcd.fillCircle(cx, my + 2, 15, MOUTH)
        else: M5.Lcd.fillRect(cx - 10, my, 20, 4, MOUTH)
    elif state == "waking_up": M5.Lcd.fillCircle(cx, my + 4, 7, MOUTH)
    elif state == "awake":
        M5.Lcd.fillCircle(cx, my, 16, MOUTH)
        M5.Lcd.fillRect(cx - 18, my - 16, 36, 16, BG)
    elif state == "angry":
        M5.Lcd.fillCircle(cx, my, 16, DARK_FEATURE)
        M5.Lcd.fillRect(cx - 18, my, 36, 16, BG)


def set_state(name):
    global state, pupil_dx, pupil_dy, closed_side, mouth_open, mouth_next
    global blink_until, blink_next, pupil_next, BG, rgb_next, rgb_on, servo_entered
    
    state = name
    BG = BG_ANGRY if name == "angry" else BG_DARK
    pupil_dx, pupil_dy, mouth_open = 0, 0, False
    closed_side = random.choice((-1, 1))
    
    now = time.ticks_ms()
    blink_until = 0
    blink_next = time.ticks_add(now, random.randint(2000, 10000))
    pupil_next = time.ticks_add(now, random.randint(700, 1500))
    mouth_next = time.ticks_add(now, random.randint(3000, 7000))
    
    _draw_face(name)
    _draw_hud(name)
    
    if name == "sleeping": _set_rgb(0x000000)
    elif name == "waking_up": _set_rgb(0x00D7DB)
    elif name == "awake": _set_rgb(0x00AA00)
    elif name == "angry":
        _set_rgb(0x000000)
        rgb_on = False
        rgb_next = now
        
    servo_entered = True
    _publish_status()


# ---- MOTORI: ARCHITETTURA A WAYPOINT ----
def _get_new_target(min_x, max_x, min_y, max_y, min_move):
    global current_x, current_y
    for _ in range(10): 
        tx = random.uniform(min_x, max_x)
        ty = random.uniform(min_y, max_y)
        if abs(tx - current_x) >= min_move or abs(ty - current_y) >= min_move:
            return tx, ty
    return random.uniform(min_x, max_x), random.uniform(min_y, max_y)


def _update_servo():
    global servo_next, servo_entered, current_x, current_y
    if sc is None: return
    now = time.ticks_ms()
    
    if servo_entered:
        servo_entered = False
        current_x, current_y = 0.0, 40.0
        try:
            sc.set_servo_angle(sc.SERVO_ID_X, float(current_x), 400, 0)
            time.sleep_ms(15)
            sc.set_servo_angle(sc.SERVO_ID_Y, float(current_y), 400, 0)
        except: pass
        servo_next = time.ticks_add(now, 500) 
        return

    if time.ticks_diff(now, servo_next) < 0:
        return

    pause_ms = 0
    duration_ms = 400

    if state == "sleeping":
        # FIX: Ripristinata l'escursione morbida a 600ms che avevi in origine
        current_x = 0.0
        current_y = 30.0 if current_y >= 35.0 else 38.0
        duration_ms = 600
        pause_ms = 2000
        
    elif state == "waking_up":
        current_x, current_y = _get_new_target(-15, 15, 30, 50, 8.0)
        duration_ms = random.randint(250, 400)
        pause_ms = random.randint(400, 800)
        
    elif state == "awake":
        current_x, current_y = _get_new_target(-30, 30, 35, 55, 10.0)
        duration_ms = random.randint(400, 600)
        pause_ms = random.randint(1000, 2500)
        
    elif state == "angry":
        current_x, current_y = _get_new_target(-35, 35, 28, 62, 10.0)
        duration_ms = random.randint(400, 600)
        pause_ms = random.randint(150, 300)

    try:
        sc.set_servo_angle(sc.SERVO_ID_X, float(current_x), duration_ms, 0)
        time.sleep_ms(15) 
        sc.set_servo_angle(sc.SERVO_ID_Y, float(current_y), duration_ms, 0)
    except Exception:
        pass

    servo_next = time.ticks_add(now, duration_ms + pause_ms)


# ---- angry RGB rapid blink ----
def _update_rgb():
    global rgb_next, rgb_on
    if sc is None or state != "angry": return
    
    now = time.ticks_ms()
    if time.ticks_diff(now, rgb_next) < 0: return
    
    rgb_on = not rgb_on
    _set_rgb(0xFF0000 if rgb_on else 0x000000)
    rgb_next = time.ticks_add(now, 80)


# ---- Sirena Polizia ----
def _update_siren():
    global siren_next, siren_high
    if state != "angry": return
        
    now = time.ticks_ms()
    if time.ticks_diff(now, siren_next) < 0: return
        
    siren_high = not siren_high
    freq = 1200 if siren_high else 800
    
    try:
        M5.Speaker.tone(freq, 250)
    except Exception:
        pass
        
    siren_next = time.ticks_add(now, 200)


# ---- face "alive" micro-motion ----
def _update_face_idle():
    global blink_until, blink_next, pupil_next, pupil_dx, pupil_dy
    global mouth_open, mouth_next
    now = time.ticks_ms()

    if state in ("awake", "waking_up"):
        if blink_until and time.ticks_diff(now, blink_until) >= 0:
            _redraw_eyes(False)
            blink_until = 0
            blink_next = time.ticks_add(now, random.randint(2000, 10000))
        elif not blink_until and time.ticks_diff(now, blink_next) >= 0:
            _redraw_eyes(True)
            blink_until = time.ticks_add(now, 60 if state == "awake" else 80)
    else:
        blink_until = 0

    if state in ("awake", "angry") and not blink_until and time.ticks_diff(now, pupil_next) >= 0:
        pupil_dx, pupil_dy = random.randint(-4, 4), random.randint(-3, 3)
        _redraw_eyes(False)
        pupil_next = time.ticks_add(now, random.randint(700, 1500))

    if state == "sleeping" and time.ticks_diff(now, mouth_next) >= 0:
        mouth_open = not mouth_open
        _redraw_mouth()
        mouth_next = time.ticks_add(now, random.randint(1500, 5000))


# ---- Pubblicazione Status, Callback e Connessione MQTT ----
def _publish_status():
    global mqtt_client, state, stars
    if mqtt_client:
        try:
            payload = '{"state": "%s", "stars": %d, "timestamp": %d}' % (state, stars, time.time())
            mqtt_client.publish(STATUS_TOPIC, payload.encode("utf-8"))
        except Exception:
            pass

def mqtt_callback(topic, msg):
    global stars
    try:
        command = msg.decode("utf-8").strip().lower()
        if command in ["sleep", "sleeping"]:
            set_state("sleeping")
        elif command in ["waking", "waking_up"]:
            set_state("waking_up")
        elif command == "awake":
            set_state("awake")
        elif command == "angry":
            set_state("angry")
        elif command == "add_star":
            stars = min(stars + 1, 10)
            _draw_stars()
            _publish_status()
        elif command in ["rm_star", "remove_star"]:
            stars = max(stars - 1, 0)
            _draw_stars()
            _publish_status()
    except Exception:
        pass

def connect_mqtt():
    global mqtt_client
    if not _HAS_MQTT: return
    try:
        mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.connect()
        mqtt_client.subscribe(CMD_TOPIC)
        _draw_hud(state) 
    except Exception:
        mqtt_client = None

def _check_mqtt():
    global mqtt_client, last_mqtt_reconnect, ping_next
    now = time.ticks_ms()
    
    if mqtt_client is None:
        if time.ticks_diff(now, last_mqtt_reconnect) > 5000:
            connect_mqtt()
            last_mqtt_reconnect = now
            ping_next = time.ticks_add(now, 20000)
        return
        
    try:
        mqtt_client.check_msg()
        
        # IL BATTITO CARDIACO (Ping): Evita la disconnessione automatica del server
        if time.ticks_diff(now, ping_next) >= 0:
            if hasattr(mqtt_client, 'ping'):
                mqtt_client.ping()
            ping_next = time.ticks_add(now, 20000)
            
    except Exception:
        try:
            mqtt_client.disconnect()
        except:
            pass
        mqtt_client = None 


def setup():
    global ip_addr, sc
    global servo_entered, gc_next

    M5.begin()
    M5.Lcd.setRotation(1)
    
    try:
        M5.Speaker.setVolume(100)
    except: pass

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    try:
        wlan.config(pm=0)
    except: pass
    
    if not wlan.isconnected():
        try: wlan.connect()
        except: pass
    
    deadline = time.ticks_add(time.ticks_ms(), 10000)
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), deadline) < 0:
        M5.update()
        time.sleep_ms(100)
    ip_addr = wlan.ifconfig()[0] if wlan.isconnected() else "offline"

    if _HAS_STACKCHAN:
        try:
            sc = StackChan(i2c=1, uart=1)
            sc.set_servo_power(enable=False, settle_ms=300)
            sc.set_servo_power(enable=True, settle_ms=500)
            sc.set_servo_torque(sc.SERVO_ID_X, enable=True)
            sc.set_servo_torque(sc.SERVO_ID_Y, enable=True)
        except Exception:
            sc = None

    gc_next = time.ticks_ms()
    servo_entered = True

    set_state("sleeping")
    connect_mqtt()


def loop():
    global gc_next
    now = time.ticks_ms()
    
    if time.ticks_diff(now, gc_next) >= 0:
        gc.collect()
        gc_next = time.ticks_add(now, 1000)

    M5.update()
    
    _check_mqtt()
    _update_face_idle()
    _update_servo()
    _update_rgb()
    _update_siren()


if __name__ == "__main__":
    try:
        setup()
        while True: loop()
    except (Exception, KeyboardInterrupt):
        pass