from rich.box import ROUNDED, HEAVY, SIMPLE, MINIMAL, Box

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ONDES BOT — Modern Neon Dark Theme v2.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Color Palette ──
C = {
    # Primary violet gradient
    "violet": "#8B5CF6",
    "violet_bright": "#A78BFA",
    "violet_dim": "#6D28D9",
    "violet_deep": "#4C1D95",
    # Accent colors
    "cyan": "#22D3EE",
    "cyan_dim": "#0891B2",
    "pink": "#F472B6",
    "pink_dim": "#DB2777",
    "emerald": "#34D399",
    "emerald_dim": "#059669",
    "amber": "#FBBF24",
    "amber_dim": "#D97706",
    "red": "#F87171",
    "red_dim": "#DC2626",
    "blue": "#60A5FA",
    # Neutrals
    "text": "#F1F5F9",
    "text_dim": "#94A3B8",
    "text_muted": "#64748B",
    "surface": "#1E293B",
    "border": "#334155",
    "border_dim": "#1E293B",
}

# ── Style Shortcuts ──
S = {
    "bot": f"bold {C['violet']}",
    "bot_glow": f"bold {C['violet_bright']}",
    "user": f"bold {C['text']}",
    "accent": f"{C['pink']}",
    "dim": f"{C['text_dim']}",
    "muted": f"{C['text_muted']}",
    "success": f"{C['emerald']}",
    "warning": f"{C['amber']}",
    "error": f"{C['red']}",
}

# ── Border Styles ──
BORDERS = {
    "header": C["violet"],
    "email": C["cyan"],
    "calendar": C["violet"],
    "task": C["emerald"],
    "response": C["violet_dim"],
    "thinking": C["pink_dim"],
    "help": C["cyan_dim"],
    "stats": C["blue"],
    "confirm": C["amber"],
    "prompt": C["violet_deep"],
    "status": C["border"],
}

BOX = ROUNDED

# ── Legacy compat ──
THEME = {
    "primary": C["violet"],
    "secondary": C["cyan"],
    "success": C["emerald"],
    "warning": C["amber"],
    "error": C["red"],
    "muted": C["text_muted"],
    "bot_name": S["bot"],
    "user_name": S["user"],
    "header": f"bold {C['violet']}",
}

SPLASH_ART = f"""
[{C['violet_dim']}]  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓[/]
[{C['violet']}]  ┃  ██████╗ ███╗   ██╗██████╗ ███████╗███████╗  ┃[/]
[{C['violet']}]  ┃ ██╔═══██╗████╗  ██║██╔══██╗██╔════╝██╔════╝  ┃[/]
[{C['violet_bright']}]  ┃ ██║   ██║██╔██╗ ██║██║  ██║█████╗  ███████╗  ┃[/]
[{C['violet_bright']}]  ┃ ██║   ██║██║╚██╗██║██║  ██║██╔══╝  ╚════██║  ┃[/]
[{C['violet']}]  ┃ ╚██████╔╝██║ ╚████║██████╔╝███████╗███████║  ┃[/]
[{C['violet_dim']}]  ┃  ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚══════╝╚══════╝  ┃[/]
[{C['violet_dim']}]  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛[/]
[{C['pink']}]              B O T  ·  v2.0[/]
"""
