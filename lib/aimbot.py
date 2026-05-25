"""
Lunar — Aimbot Core (v2.1)
Lê configurações de lib/config/settings.json geradas pelo menu.py.
As configurações são recarregadas automaticamente a cada segundo —
qualquer alteração no menu é aplicada em tempo real, sem reiniciar.
"""

import ctypes, cv2, json, math, mss, numpy as np
import os, sys, time, threading, queue, torch, uuid, win32api
from termcolor import colored

# ── Estruturas ctypes para SendInput ──────────────────────────────────────────
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

# ── Mapeamento keybind string → virtual key code ──────────────────────────────
# "None" não está no dict → .get() retorna None → sempre ativo
KEYBIND_VK = {
    "LMB": 0x01, "RMB": 0x02, "MMB": 0x04, "M4": 0x05, "M5": 0x06,
    "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,
    "CAPSLOCK": 0x14, "TAB": 0x09,
}
for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    KEYBIND_VK.setdefault(c, 0x41 + i)
for i in range(10):
    KEYBIND_VK[str(i)] = 0x30 + i

# ── Aim bone → offset vertical na bbox ───────────────────────────────────────
BONE_OFFSET = {
    "Head":   0.10,
    "Neck":   0.22,
    "Chest":  0.40,
    "Pelvis": 0.65,
}


def _busy_sleep(duration, _get=time.perf_counter):
    if duration <= 0: return
    end = _get() + duration
    while _get() < end: pass


def _send_mouse_move(dx, dy, extra, ii):
    ii.mi = MouseInput(dx, dy, 0, 0x0001, 0, ctypes.pointer(extra))
    inp = Input(ctypes.c_ulong(0), ii)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def _send_click():
    ctypes.windll.user32.mouse_event(0x0002)
    _busy_sleep(0.005)
    ctypes.windll.user32.mouse_event(0x0004)


def _key_held(vk) -> bool:
    """Se vk for None (keybind = "None"), retorna True — sempre ativo."""
    if vk is None:
        return True
    return win32api.GetKeyState(vk) in (-127, -128)


def _resolve_vk(keybind_str):
    """Converte string de keybind para VK code. "None" → None (sempre ativo)."""
    if not keybind_str or keybind_str.strip().lower() == "none":
        return None
    return KEYBIND_VK.get(keybind_str.upper())


# ── Thread: recarrega settings.json em tempo real ─────────────────────────────
class SettingsWatcher(threading.Thread):
    """
    Monitora settings.json e atualiza o dict compartilhado sempre que
    o arquivo muda. Intervalo: 1 segundo.
    """
    def __init__(self, settings_dict, path):
        super().__init__(daemon=True)
        self._s    = settings_dict
        self._path = path
        self._stop = threading.Event()
        self._last_mtime = 0.0

    def stop(self): self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                mtime = os.path.getmtime(self._path)
                if mtime != self._last_mtime:
                    with open(self._path) as f:
                        new = json.load(f)
                    self._s.update(new)
                    self._last_mtime = mtime
            except Exception:
                pass
            time.sleep(1.0)


# ── Thread: movimento do mouse ────────────────────────────────────────────────
class MouseThread(threading.Thread):
    """
    Recebe coordenadas do alvo via fila (maxsize=1).
    Usa keybind do aimbot — None = sempre ativo.
    """
    def __init__(self, sens_config, settings, pixel_increment=1, mouse_delay=0.0001):
        super().__init__(daemon=True)
        self.scale       = sens_config["targeting_scale"]
        self.pixel_inc   = pixel_increment
        self.mouse_delay = mouse_delay
        self.settings    = settings
        self._q          = queue.Queue(maxsize=1)
        self._extra      = ctypes.c_ulong(0)
        self._ii         = Input_I()
        self._stop       = threading.Event()

    def update_target(self, x, y):
        if self._q.full():
            try: self._q.get_nowait()
            except queue.Empty: pass
        try: self._q.put_nowait((x, y))
        except queue.Full: pass

    def stop(self): self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                x, y = self._q.get(timeout=0.05)
            except queue.Empty:
                continue

            ab  = self.settings["aimbot"]
            vk  = _resolve_vk(ab["keybind"])

            if not ab["auto_aim"] and not _key_held(vk):
                continue

            strength = ab["strength"] / 100.0
            scale    = self.scale * strength
            diff_x   = (x - 960) * scale / self.pixel_inc
            diff_y   = (y - 540) * scale / self.pixel_inc
            length   = int(math.dist((0, 0), (diff_x, diff_y)))
            if length == 0: continue

            unit_x = (diff_x / length) * self.pixel_inc
            unit_y = (diff_y / length) * self.pixel_inc
            sum_x = sum_y = 0

            for k in range(length):
                if not self._q.empty(): break
                if not ab["auto_aim"] and not _key_held(_resolve_vk(ab["keybind"])): break
                rx = round(unit_x * k - sum_x)
                ry = round(unit_y * k - sum_y)
                sum_x += rx; sum_y += ry
                _send_mouse_move(rx, ry, self._extra, self._ii)
                _busy_sleep(self.mouse_delay)


# ── Thread: triggerbot ────────────────────────────────────────────────────────
class TriggerbotThread(threading.Thread):
    """
    Três modos de operação:
    Toggle   — aperta a tecla para ligar/desligar. Atira quando há alvo travado.
    Hold     — ativo somente enquanto a tecla estiver pressionada. Atira quando há alvo travado.
    Auto-Tap — clica sozinho a cada [tap_interval] ms independente de alvo ou tecla.
    """
    def __init__(self, settings, lock_flag):
        super().__init__(daemon=True)
        self.settings        = settings
        self.lock_flag       = lock_flag
        self._stop           = threading.Event()
        self._active         = False
        self._key_was_down   = False
        self._at_first_shot  = True   # controla se é o primeiro tiro do alvo atual
        self._last_target    = None   # momento em que o alvo foi detectado pela primeira vez
        self._lost_at        = None   # momento em que o alvo sumiu (grace period)

    def stop(self): self._stop.set()

    def run(self):
        fired_at = 0.0

        while not self._stop.is_set():
            tb = self.settings["triggerbot"]

            if not tb["enabled"]:
                self._active        = False
                self._key_was_down  = False
                self._at_first_shot = True
                self._last_target   = None
                time.sleep(0.05)
                continue

            mode    = tb.get("mode", "Toggle")
            vk      = _resolve_vk(tb.get("keybind", "None"))
            is_down = _key_held(vk) if vk else False
            delay   = tb["trigger_delay"] / 1000.0
            interval = tb.get("tap_interval", 100) / 1000.0
            now     = time.perf_counter()

            # ── Auto-Tap ──────────────────────────────────────────────────────
            # Primeiro tiro: aguarda trigger_delay desde que o alvo apareceu
            # Tiros seguintes: só dispara se passou >= tap_interval desde o último tiro
            # Grace period: lock_flag pode piscar entre frames — só reseta se o
            # alvo ficou ausente por mais de 150ms (evita resets falsos)
            if mode == "Auto-Tap":
                locked = self.lock_flag.is_set()

                if locked:
                    self._lost_at = None   # alvo presente, limpa o timer de perda

                    # Marca o momento em que o alvo foi detectado pela primeira vez
                    if self._last_target is None:
                        self._last_target = now

                    if self._at_first_shot:
                        # Primeiro tiro: aguarda trigger_delay
                        if now - self._last_target >= delay:
                            _send_click()
                            fired_at            = time.perf_counter()
                            self._at_first_shot = False
                    else:
                        # Tiros seguintes: respeita tap_interval
                        if now - fired_at >= interval:
                            _send_click()
                            fired_at = time.perf_counter()

                else:
                    # Alvo perdido — inicia grace period de 150ms antes de resetar
                    if self._lost_at is None:
                        self._lost_at = now
                    elif now - self._lost_at >= 0.15:
                        self._at_first_shot = True
                        self._last_target   = None
                        self._lost_at       = None

                time.sleep(0.004)
                continue

            # ── Toggle: borda de subida da tecla liga/desliga ─────────────────
            if mode == "Toggle":
                if vk is None:
                    self._active = True
                else:
                    if is_down and not self._key_was_down:
                        self._active = not self._active
                    self._key_was_down = is_down
                should_fire = self._active

            # ── Hold: ativo enquanto a tecla estiver pressionada ──────────────
            elif mode == "Hold":
                should_fire = is_down if vk else True
                self._key_was_down = is_down

            else:
                should_fire = False

            # Toggle/Hold: dispara quando ativo, alvo travado e delay passou
            if should_fire and self.lock_flag.is_set():
                if now - fired_at >= delay:
                    _send_click()
                    fired_at = time.perf_counter()

            time.sleep(0.004)   # ~250 Hz de polling





# ── Aimbot principal ──────────────────────────────────────────────────────────
class Aimbot:
    screen          = mss.mss()
    pixel_increment = 1

    with open("lib/config/config.json") as _f:
        sens_config = json.load(_f)
    with open("lib/config/settings.json") as _f:
        settings = json.load(_f)

    def __init__(self, box_constant=416, collect_data=False,
                 mouse_delay=0.0001, debug=False):
        self.box_constant = box_constant
        self.mouse_delay  = mouse_delay
        self.debug        = debug
        self.collect_data = collect_data
        self.target_locked = threading.Event()

        print("[INFO] Carregando modelo…")
        self.model = torch.hub.load(
            "ultralytics/yolov5", "custom",
            path="lib/best.pt", force_reload=True
        )
        if torch.cuda.is_available():
            print(colored("CUDA [ENABLED]", "green"))
        else:
            print(colored("[!] CUDA indisponível", "red"))

        self.model.conf = 0.45
        self.model.iou  = 0.45

        self.mouse_thread   = MouseThread(Aimbot.sens_config, Aimbot.settings,
                                          Aimbot.pixel_increment, mouse_delay)
        self.trigger_thread = TriggerbotThread(Aimbot.settings, self.target_locked)
        self.watcher = SettingsWatcher(Aimbot.settings, "lib/config/settings.json")

        for t in (self.mouse_thread, self.trigger_thread, self.watcher):
            t.start()

        print("[INFO] Threads iniciadas  |  F2 → sair")

    def start(self):
        print("[INFO] Captura iniciada")
        hw  = ctypes.windll.user32.GetSystemMetrics(0) / 2
        hh  = ctypes.windll.user32.GetSystemMetrics(1) / 2
        box = {
            "left":   int(hw - self.box_constant // 2),
            "top":    int(hh - self.box_constant // 2),
            "width":  self.box_constant,
            "height": self.box_constant,
        }
        half = self.box_constant / 2
        collect_pause = 0.0

        while True:
            t0    = time.perf_counter()
            frame = np.array(Aimbot.screen.grab(box))
            if self.collect_data:
                orig_frame = np.copy(frame)

            results       = self.model(frame)
            ab            = Aimbot.settings["aimbot"]
            tb            = Aimbot.settings["triggerbot"]
            fov_r         = ab["fov"] / 2
            bone_off      = BONE_OFFSET.get(ab["aim_bone"], 0.10)
            player_in_frame = False

            # Círculo de FOV
            cv2.circle(frame, (int(half), int(half)), int(fov_r), (60, 60, 100), 1)

            closest  = None
            min_dist = float("inf")

            if len(results.xyxy[0]) != 0:
                for *bc, conf, cls in results.xyxy[0]:
                    x1, y1 = int(bc[0].item()), int(bc[1].item())
                    x2, y2 = int(bc[2].item()), int(bc[3].item())
                    conf   = conf.item()
                    h      = y2 - y1
                    hx     = int((x1 + x2) / 2)
                    hy     = int(y1 + h * bone_off)
                    own    = x1 < 15 or (x1 < self.box_constant / 5
                                         and y2 > self.box_constant / 1.2)
                    dist   = math.dist((hx, hy), (half, half))

                    if not own:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (244, 113, 115), 2)
                        cv2.putText(frame, f"{int(conf*100)}%", (x1, y1),
                                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (244, 113, 116), 2)
                        if dist <= fov_r and dist < min_dist:
                            min_dist = dist
                            closest  = {"x1": x1, "y1": y1, "hx": hx, "hy": hy}
                    else:
                        player_in_frame = True

            if closest:
                hx, hy = closest["hx"], closest["hy"]
                ax, ay = hx + box["left"], hy + box["top"]
                thr    = 5
                locked = (960 - thr <= ax <= 960 + thr and
                          540 - thr <= ay <= 540 + thr)

                if locked: self.target_locked.set()
                else:      self.target_locked.clear()

                cv2.circle(frame, (hx, hy), 5, (115, 244, 113), -1)
                cv2.line(frame, (hx, hy), (int(half), int(half)), (244, 242, 113), 2)
                label = "LOCKED" if locked else "TARGETING"
                color = (115, 244, 113) if locked else (115, 113, 244)
                cv2.putText(frame, label, (closest["x1"] + 40, closest["y1"]),
                            cv2.FONT_HERSHEY_DUPLEX, 0.5, color, 2)

                if ab["enabled"]:
                    self.mouse_thread.update_target(ax, ay)
            else:
                self.target_locked.clear()

            if (self.collect_data and time.perf_counter() - collect_pause > 1
                    and ab["enabled"] and not player_in_frame):
                cv2.imwrite(f"lib/data/{str(uuid.uuid4())}.jpg", orig_frame)
                collect_pause = time.perf_counter()

            # HUD
            fps = int(1 / max(time.perf_counter() - t0, 1e-9))
            tb_key = tb["keybind"]
            hud = [
                (f"FPS: {fps}",
                 (5, 28), (113, 116, 244)),
                (f"BONE:{ab['aim_bone']}  STR:{ab['strength']}%  FOV:{ab['fov']}px",
                 (5, 50), (170, 170, 255)),
                (f"AIMBOT:  {'ON' if ab['enabled'] else 'OFF'}  "
                 f"KEY:{ab['keybind']}",
                 (5, 70), (115, 244, 113) if ab["enabled"] else (180, 80, 80)),
                (f"TRIGGER: {'ON' if tb['enabled'] else 'OFF'}  "
                 f"KEY:{tb_key}  DLY:{tb['trigger_delay']}ms",
                 (5, 90), (115, 244, 113) if tb["enabled"] else (180, 80, 80)),
            ]
            for txt, pos, col in hud:
                cv2.putText(frame, txt, pos, cv2.FONT_HERSHEY_DUPLEX, 0.4, col, 1)

            cv2.imshow("Lunar Vision", frame)
            if cv2.waitKey(1) & 0xFF == ord("0"):
                break

    def clean_up(self):
        print("\n[INFO] Encerrando…")
        for t in (self.mouse_thread, self.trigger_thread, self.watcher):
            t.stop()
        Aimbot.screen.close()
        os._exit(0)


if __name__ == "__main__":
    print("Execute lunar.py ou menu.py")