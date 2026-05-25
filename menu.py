"""
Lunar — Visual Configuration Menu (v2.1)
Execute: python menu.py
"""

import tkinter as tk
from tkinter import ttk
import json, os, subprocess, signal, sys

# ── Caminhos ──────────────────────────────────────────────────────────────────
CONFIG_DIR = "lib/config"
SETT_PATH  = os.path.join(CONFIG_DIR, "settings.json")
SENS_PATH  = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_SETTINGS = {
    "aimbot": {
        "enabled": True,
        "aim_bone": "Head",
        "strength": 50,
        "fov": 150,
        "auto_aim": False,
        "target_prediction": False,
        "keybind": "None",
    },
    "triggerbot": {
        "enabled": False,
        "mode": "Toggle",
        "trigger_delay": 50,
        "tap_interval": 100,
        "keybind": "None",
    },
    "anti_recoil": {
        "enabled": False,
        "pull_strength": 5,
    },
}

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0b0b13"
PANEL  = "#11111c"
CARD   = "#18182a"
BORDER = "#252540"
ACCENT = "#7055ff"
CYAN   = "#00d4ff"
GREEN  = "#00e676"
ORANGE = "#ff9800"
RED    = "#ff4455"
TEXT   = "#dcdcf0"
DIM    = "#55556a"
HOVER  = "#21213a"
WHITE  = "#ffffff"


# ── Toggle Switch ─────────────────────────────────────────────────────────────
class Toggle(tk.Canvas):
    W, H, R = 46, 24, 11

    def __init__(self, parent, variable, on_change=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=CARD, bd=0, highlightthickness=0, cursor="hand2", **kw)
        self.var = variable
        self.on_change = on_change
        self._draw()
        self.bind("<Button-1>", self._click)

    def _draw(self):
        self.delete("all")
        on = self.var.get()
        track = ACCENT if on else "#2e2e48"
        knob_x = self.W - self.R - 3 if on else self.R + 3
        cy = self.H // 2
        self.create_oval(2, 2, self.H - 2, self.H - 2, fill=track, outline="")
        self.create_oval(self.W - self.H + 2, 2, self.W - 2, self.H - 2, fill=track, outline="")
        self.create_rectangle(self.H // 2, 2, self.W - self.H // 2, self.H - 2,
                              fill=track, outline="")
        self.create_oval(knob_x - self.R, cy - self.R,
                         knob_x + self.R, cy + self.R,
                         fill=WHITE, outline="")

    def _click(self, _=None):
        self.var.set(not self.var.get())
        self._draw()
        if self.on_change:
            self.on_change()


# ── Keybind Button ─────────────────────────────────────────────────────────────
class KeybindBtn(tk.Frame):
    MOUSE = {1: "LMB", 2: "RMB", 3: "MMB", 4: "M4", 5: "M5"}
    IGNORE = {"shift_l", "shift_r", "control_l", "control_r",
              "alt_l", "alt_r", "super_l", "super_r"}

    def __init__(self, parent, variable, on_change=None, **kw):
        super().__init__(parent, bg=CARD, **kw)
        self.var       = variable
        self.on_change = on_change
        self._waiting  = False

        self.btn = tk.Button(self, textvariable=variable,
                             bg=BORDER, fg=TEXT, relief="flat",
                             font=("Consolas", 9), width=9, cursor="hand2",
                             activebackground=HOVER, activeforeground=TEXT,
                             command=self._start)
        self.btn.pack(side="left")

        # Botão X para limpar (volta para None)
        tk.Button(self, text="[x]", bg=CARD, fg=DIM, relief="flat",
                  font=("Consolas", 8), padx=3, cursor="hand2",
                  activebackground=CARD, activeforeground=RED,
                  command=self._clear).pack(side="left", padx=(2, 0))

    def _clear(self):
        self.var.set("None")
        if self.on_change: self.on_change()

    def _start(self):
        if self._waiting: return
        self._waiting = True
        self.var.set("  . . .")
        self.btn.config(bg=ACCENT)
        self.btn.bind("<Key>",    self._key)
        self.btn.bind("<Button>", self._mouse)
        self.btn.focus_set()

    def _key(self, e):
        if not self._waiting: return
        if e.keysym.lower() == "escape":   # ESC cancela e volta para None
            self.var.set("None")
            self._done()
            return
        if e.keysym.lower() in self.IGNORE: return
        self.var.set(e.keysym.upper())
        self._done()

    def _mouse(self, e):
        if not self._waiting: return
        self.var.set(self.MOUSE.get(e.num, f"M{e.num}"))
        self._done()

    def _done(self):
        self._waiting = False
        self.btn.config(bg=BORDER)
        self.btn.unbind("<Key>")
        self.btn.unbind("<Button>")
        if self.on_change: self.on_change()


# ── Helpers de linha ──────────────────────────────────────────────────────────
def setting_row(parent, label, widget_builder):
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill="x", pady=3)
    tk.Label(row, text=label, bg=CARD, fg=DIM,
             font=("Consolas", 9), width=22, anchor="w").pack(side="left", padx=(0, 8))
    widget_builder(row)
    return row

def toggle_row(parent, label, var, on_change=None):
    setting_row(parent, label, lambda p: Toggle(p, var, on_change=on_change).pack(side="right"))

def slider_row(parent, label, var, lo, hi, unit="", on_change=None):
    def build(p):
        val_lbl = tk.Label(p, text=f"{int(var.get())}{unit}",
                           bg=CARD, fg=CYAN, font=("Consolas", 9), width=6, anchor="e")
        val_lbl.pack(side="right")
        def upd(v):
            val_lbl.config(text=f"{int(float(v))}{unit}")
            if on_change: on_change()
        ttk.Scale(p, from_=lo, to=hi, orient="horizontal",
                  variable=var, command=upd).pack(side="right", fill="x", expand=True, padx=4)
    setting_row(parent, label, build)

def combo_row(parent, label, var, options, on_change=None):
    def build(p):
        cb = ttk.Combobox(p, textvariable=var, values=options,
                          state="readonly", width=12, font=("Consolas", 9))
        if on_change: cb.bind("<<ComboboxSelected>>", lambda _: on_change())
        cb.pack(side="right")
    setting_row(parent, label, build)

def keybind_row(parent, label, var, on_change=None):
    setting_row(parent, label,
                lambda p: KeybindBtn(p, var, on_change=on_change).pack(side="right"))

def make_card(parent, title, color=ACCENT):
    wrap = tk.Frame(parent, bg=BORDER)
    wrap.pack(fill="x", pady=(0, 10))
    tk.Frame(wrap, bg=color, height=2).pack(fill="x")
    inner = tk.Frame(wrap, bg=CARD, padx=14, pady=10)
    inner.pack(fill="x")
    tk.Label(inner, text=f"  {title.upper()}", bg=CARD, fg=color,
             font=("Consolas", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 8))
    return inner


# ── Menu principal ────────────────────────────────────────────────────────────
class LunarMenu:

    SECTIONS = [
        ("aimbot",      "◎   AIMBOT",      ACCENT),
        ("triggerbot",  "⊡   TRIGGERBOT",  ORANGE),
        ("config",      "⚙   SENSIBILIDADE", CYAN),
    ]

    def __init__(self):
        self._load_settings()
        self._aimbot_proc = None
        self._save_job    = None   # debounce id

        self.root = tk.Tk()
        self._build_vars()
        self.root.title("Lunar — Configuration")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry("700x540")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._apply_style()
        self._build_ui()
        self._show("aimbot")
        self._poll_status()   # inicia verificação periódica do processo

    # ── Settings ──────────────────────────────────────────────────────────────
    def _load_settings(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(SETT_PATH):
            with open(SETT_PATH) as f:
                data = json.load(f)
            for sec, vals in DEFAULT_SETTINGS.items():
                for key, val in vals.items():
                    data.setdefault(sec, {})[key] = data.get(sec, {}).get(key, val)
            self.s = data
        else:
            self.s = {sec: dict(v) for sec, v in DEFAULT_SETTINGS.items()}

    def _build_vars(self):
        ab, tb = self.s["aimbot"], self.s["triggerbot"]
        # lê config.json de sensibilidade
        cfg = {}
        if os.path.exists(SENS_PATH):
            with open(SENS_PATH) as f:
                cfg = json.load(f)
        self.v = {
            "ab_en":   tk.BooleanVar(value=ab["enabled"]),
            "ab_bone": tk.StringVar(value=ab["aim_bone"]),
            "ab_str":  tk.DoubleVar(value=ab["strength"]),
            "ab_fov":  tk.DoubleVar(value=ab["fov"]),
            "ab_auto": tk.BooleanVar(value=ab["auto_aim"]),
            "ab_pred": tk.BooleanVar(value=ab["target_prediction"]),
            "ab_key":  tk.StringVar(value=ab["keybind"]),
            "tb_en":   tk.BooleanVar(value=tb["enabled"]),
            "tb_mode": tk.StringVar(value=tb.get("mode", "Toggle")),
            "tb_dly":  tk.DoubleVar(value=tb["trigger_delay"]),
            "tb_tap":  tk.DoubleVar(value=tb.get("tap_interval", 100)),
            "tb_key":  tk.StringVar(value=tb["keybind"]),
            "cfg_xy":  tk.DoubleVar(value=cfg.get("xy_sens", 6.0)),
            "cfg_tgt": tk.DoubleVar(value=cfg.get("targeting_sens", 0.5)),
        }
        # trace em todas as vars para auto-save
        for var in self.v.values():
            var.trace_add("write", lambda *_: self._schedule_save())

    def _schedule_save(self):
        """Debounce: salva 400ms após a última alteração."""
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(400, self._save)

    def _collect(self):
        return {
            "aimbot": {
                "enabled":           self.v["ab_en"].get(),
                "aim_bone":          self.v["ab_bone"].get(),
                "strength":          int(self.v["ab_str"].get()),
                "fov":               int(self.v["ab_fov"].get()),
                "auto_aim":          self.v["ab_auto"].get(),
                "target_prediction": self.v["ab_pred"].get(),
                "keybind":           self.v["ab_key"].get(),
            },
            "triggerbot": {
                "enabled":       self.v["tb_en"].get(),
                "mode":          self.v["tb_mode"].get(),
                "trigger_delay": int(self.v["tb_dly"].get()),
                "tap_interval":  int(self.v["tb_tap"].get()),
                "keybind":       self.v["tb_key"].get(),
            },

        }

    def _save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # salva settings.json
        with open(SETT_PATH, "w") as f:
            json.dump(self._collect(), f, indent=2)
        # salva config.json com sensibilidade em tempo real
        try:
            xy  = round(self.v["cfg_xy"].get(),  4)
            tgt = round(self.v["cfg_tgt"].get(), 4)
            sens = {
                "xy_sens":         xy,
                "targeting_sens":  tgt,
                "xy_scale":        round(10 / xy, 6)            if xy          else 0,
                "targeting_scale": round(1000 / (tgt * xy), 6) if xy and tgt  else 0,
            }
            with open(SENS_PATH, "w") as f:
                json.dump(sens, f, indent=2)
        except Exception:
            pass
        self._flash_status("●  SALVO", CYAN, revert_ms=1500)

    # ── Status do processo ────────────────────────────────────────────────────
    def _poll_status(self):
        """Verifica a cada 1s se o aimbot ainda está rodando."""
        if self._aimbot_proc:
            if self._aimbot_proc.poll() is not None:
                self._aimbot_proc = None
                self._update_buttons(running=False)
                self._flash_status("●  PARADO", RED)
        self.root.after(1000, self._poll_status)

    def _update_buttons(self, running: bool):
        if running:
            self._btn_launch.config(state="disabled", bg=DIM)
            self._btn_stop.config(state="normal", bg=RED)
        else:
            self._btn_launch.config(state="normal", bg=ACCENT)
            self._btn_stop.config(state="disabled", bg=DIM)

    def _flash_status(self, text, color, revert_ms=0):
        self._status_lbl.config(text=text, fg=color)
        if revert_ms:
            self.root.after(revert_ms, lambda: self._status_lbl.config(
                text="●  PRONTO", fg=GREEN))

    # ── Ações Launch / Stop ───────────────────────────────────────────────────
    def _launch(self):
        if self._aimbot_proc and self._aimbot_proc.poll() is None:
            return
        self._save()
        self._aimbot_proc = subprocess.Popen(
            [sys.executable, "lunar.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        )
        self._update_buttons(running=True)
        self._flash_status("●  RODANDO", GREEN)

    def _stop(self):
        if self._aimbot_proc:
            self._aimbot_proc.terminate()
            self._aimbot_proc = None
        self._update_buttons(running=False)
        self._flash_status("●  PARADO", RED)

    def _on_close(self):
        self._stop()
        self.root.destroy()

    # ── Estilo ttk ────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TScale", background=CARD, troughcolor=BORDER,
                    sliderthickness=14, sliderrelief="flat")
        s.configure("TCombobox", fieldbackground=BORDER, background=BORDER,
                    foreground=TEXT, arrowcolor=DIM,
                    selectbackground=ACCENT, selectforeground=TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", BORDER)],
              foreground=[("readonly", TEXT)])

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=PANEL, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◆", bg=PANEL, fg=ACCENT,
                 font=("Consolas", 15, "bold")).pack(side="left", padx=(18, 4))
        tk.Label(hdr, text="LUNAR", bg=PANEL, fg=TEXT,
                 font=("Consolas", 13, "bold")).pack(side="left")
        tk.Label(hdr, text="— neural network aim assist",
                 bg=PANEL, fg=DIM, font=("Consolas", 8)).pack(side="left", padx=8)
        badge = tk.Frame(hdr, bg=ACCENT, padx=8, pady=3)
        badge.pack(side="right", padx=18, pady=14)
        tk.Label(badge, text="v2.1", bg=ACCENT, fg=WHITE,
                 font=("Consolas", 8, "bold")).pack()

        # Body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        # Sidebar
        self._nav_btns = {}
        side = tk.Frame(body, bg=PANEL, width=160)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(side, bg=PANEL, height=16).pack()
        for key, label, color in self.SECTIONS:
            btn = tk.Button(side, text=label, bg=PANEL, fg=DIM,
                            font=("Consolas", 9), relief="flat",
                            anchor="w", padx=16, pady=11, cursor="hand2",
                            activebackground=HOVER, activeforeground=TEXT,
                            command=lambda k=key: self._show(k))
            btn.pack(fill="x")
            self._nav_btns[key] = (btn, color)

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Conteúdo scrollável
        outer = tk.Frame(body, bg=BG)
        outer.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.content = tk.Frame(canvas, bg=BG, padx=24, pady=20)
        self.content.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # Footer
        ftr = tk.Frame(self.root, bg=PANEL, height=56)
        ftr.pack(fill="x", side="bottom")
        ftr.pack_propagate(False)

        self._status_lbl = tk.Label(ftr, text="●  PRONTO",
                                    bg=PANEL, fg=GREEN, font=("Consolas", 9))
        self._status_lbl.pack(side="left", padx=18)

        self._btn_stop = tk.Button(ftr, text="  PARAR  ",
                  bg=DIM, fg=WHITE, relief="flat",
                  font=("Consolas", 9), padx=4, pady=6, cursor="hand2",
                  state="disabled",
                  activebackground="#cc2233", activeforeground=WHITE,
                  command=self._stop)
        self._btn_stop.pack(side="right", padx=(0, 8), pady=10)

        self._btn_launch = tk.Button(ftr, text="  ▶  INICIAR  ",
                  bg=ACCENT, fg=WHITE, relief="flat",
                  font=("Consolas", 10, "bold"), padx=4, pady=6, cursor="hand2",
                  activebackground="#5a45dd", activeforeground=WHITE,
                  command=self._launch)
        self._btn_launch.pack(side="right", padx=18, pady=10)

    # ── Navegação entre seções ────────────────────────────────────────────────
    def _show(self, key):
        for k, (btn, color) in self._nav_btns.items():
            btn.config(bg=HOVER if k == key else PANEL,
                       fg=color if k == key else DIM)
        for w in self.content.winfo_children():
            w.destroy()
        getattr(self, f"_section_{key}")()

    # ── Seções ────────────────────────────────────────────────────────────────
    def _section_aimbot(self):
        tk.Label(self.content, text="AIMBOT", bg=BG, fg=ACCENT,
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(0, 14))

        g = make_card(self.content, "Geral", ACCENT)
        toggle_row(g, "Habilitado", self.v["ab_en"])

        t = make_card(self.content, "Mira", CYAN)
        combo_row(t, "Aim Bone", self.v["ab_bone"],
                  ["Head", "Neck", "Chest", "Pelvis"])
        slider_row(t, "Strength  (suavidade)", self.v["ab_str"], 1, 100, "%")
        slider_row(t, "FOV  (raio de detecção)", self.v["ab_fov"], 50, 500, "px")
        toggle_row(t, "Auto-Aim  (sem tecla)", self.v["ab_auto"])
        toggle_row(t, "Target Prediction",     self.v["ab_pred"])

        i = make_card(self.content, "Tecla de Ativação", ORANGE)
        keybind_row(i, "Tecla  (None = sempre ativo)", self.v["ab_key"])

        tk.Label(self.content,
                 text="[i]  Clique no botao para capturar uma tecla.\n   Deixe como RMB para usar o botao direito do mouse.",
                 bg=BG, fg=DIM, font=("Consolas", 8), justify="left"
                 ).pack(anchor="w", pady=(8, 0))

    def _section_triggerbot(self):
        tk.Label(self.content, text="TRIGGERBOT", bg=BG, fg=ORANGE,
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(self.content,
                 text="Atira automaticamente quando um alvo esta sob o crosshair.",
                 bg=BG, fg=DIM, font=("Consolas", 8)).pack(anchor="w", pady=(0, 14))

        g = make_card(self.content, "Geral", ORANGE)
        toggle_row(g, "Habilitado", self.v["tb_en"])

        m = make_card(self.content, "Modo de Ativacao", ORANGE)
        combo_row(m, "Modo", self.v["tb_mode"], ["Toggle", "Hold", "Auto-Tap"])

        t = make_card(self.content, "Timing", CYAN)
        slider_row(t, "Trigger Delay  (delay do disparo)", self.v["tb_dly"], 0, 500, "ms")
        slider_row(t, "Tap Interval   (auto-tap)", self.v["tb_tap"], 10, 10000, "ms")

        i = make_card(self.content, "Tecla de Ativacao", ORANGE)
        keybind_row(i, "Tecla", self.v["tb_key"])

        tk.Label(self.content,
                 text="[i]  Toggle   - aperta para ligar, aperta de novo para desligar.\n"
                      "     Hold     - ativo somente enquanto segurar a tecla.\n"
                      "     Auto-Tap - clica sozinho a cada [Tap Interval] ms.",
                 bg=BG, fg=DIM, font=("Consolas", 8), justify="left"
                 ).pack(anchor="w", pady=(8, 0))

    def _section_config(self):
        tk.Label(self.content, text="SENSIBILIDADE", bg=BG, fg=CYAN,
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(self.content,
                 text="Ajuste os valores de sensibilidade do jogo. Salvo em config.json.",
                 bg=BG, fg=DIM, font=("Consolas", 8)).pack(anchor="w", pady=(0, 14))

        s = make_card(self.content, "Valores do Jogo", CYAN)
        slider_row(s, "Sensibilidade X/Y", self.v["cfg_xy"],  0.1, 30.0, "")
        slider_row(s, "Targeting Sens",    self.v["cfg_tgt"], 0.1, 5.0,  "")

        # preview dos valores calculados
        def update_preview(*_):
            try:
                xy  = round(self.v["cfg_xy"].get(), 4)
                tgt = round(self.v["cfg_tgt"].get(), 4)
                xs  = round(10 / xy, 4) if xy else 0
                ts  = round(1000 / (tgt * xy), 4) if xy and tgt else 0
                preview_lbl.config(
                    text=f"  xy_scale = {xs}     targeting_scale = {ts}"
                )
            except Exception:
                pass

        self.v["cfg_xy"].trace_add("write",  update_preview)
        self.v["cfg_tgt"].trace_add("write", update_preview)

        p = make_card(self.content, "Valores Calculados (leitura)", BORDER)
        preview_lbl = tk.Label(p, text="", bg=CARD, fg=CYAN,
                               font=("Consolas", 9), anchor="w")
        preview_lbl.pack(fill="x")
        update_preview()

        tk.Label(self.content,
                 text="[i]  X/Y e Targeting devem ser iguais as configuracoes do jogo.\n"
                      "     Os valores calculados sao gravados automaticamente ao salvar.",
                 bg=BG, fg=DIM, font=("Consolas", 8), justify="left"
                 ).pack(anchor="w", pady=(8, 0))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    LunarMenu().run()