"""
Lunar — Entry Point (v2.1)
Execute via menu.py → botão INICIAR
Ou direto: python lunar.py
"""
import json, os, sys
from pynput import keyboard
from termcolor import colored

def on_release(key):
    try:
        if key == keyboard.Key.f2:
            lunar.clean_up()
    except NameError:
        pass

def setup_sensitivity():
    os.makedirs("lib/config", exist_ok=True)
    print("[INFO] Sensibilidade X e Y no jogo deve ser igual")
    def prompt(msg):
        while True:
            try: return float(input(msg))
            except ValueError: print("[!] Digite apenas o número (ex: 6.9)")
    xy  = prompt("Sensibilidade X/Y (in-game): ")
    tgt = prompt("Targeting Sensitivity (in-game): ")
    cfg = {
        "xy_sens": xy, "targeting_sens": tgt,
        "xy_scale": 10 / xy,
        "targeting_scale": 1000 / (tgt * xy),
    }
    with open("lib/config/config.json", "w") as f:
        json.dump(cfg, f, indent=2)
    print("[INFO] Sensibilidade configurada")

def ensure_settings():
    path = "lib/config/settings.json"
    if not os.path.exists(path):
        default = {
            "aimbot":      {"enabled": True,  "aim_bone": "Head",
                            "strength": 50,   "fov": 150,
                            "auto_aim": False, "target_prediction": False,
                            "keybind": "None"},
            "triggerbot":  {"enabled": False, "trigger_delay": 50, "keybind": "None"},
            "anti_recoil": {"enabled": False, "pull_strength": 5},
        }
        os.makedirs("lib/config", exist_ok=True)
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
        print("[INFO] settings.json criado com valores padrão")

def main():
    global lunar
    lunar = Aimbot(collect_data="collect_data" in sys.argv)
    lunar.start()

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

    print(colored("""
    | |
    | |    _   _ _ __   __ _ _ __
    | |   | | | | '_ \\ / _` | '__|
    | |___| |_| | | | | (_| | |
    \\_____/\\__,_|_| |_|\\__,_|_|
    v2.1  —  F2 para sair
    """, "yellow"))

    if not os.path.exists("lib/config/config.json") or "setup" in sys.argv:
        setup_sensitivity()

    ensure_settings()

    if "collect_data" in sys.argv and not os.path.exists("lib/data"):
        os.makedirs("lib/data")

    from lib.aimbot import Aimbot

    listener = keyboard.Listener(on_release=on_release)
    listener.start()
    main()