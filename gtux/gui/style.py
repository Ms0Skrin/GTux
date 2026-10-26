"""Пастельная тема окна. Две палитры (светлая/тёмная) переключаются вслед за системной темой."""

from __future__ import annotations

# Цвета статусов: (фон плашки, цвет текста/иконки)
LIGHT = {
    "window": "#f6f4fb", "view": "#ffffff", "card": "#ffffff", "sidebar": "#efecf7",
    "accent": "#8e7cc3", "accent_fg": "#ffffff", "muted": "#6c6783", "border": "rgba(108,103,131,0.12)",
    "ok": ("#d9f2e6", "#2e7a57"), "warn": ("#fcebd3", "#9c5c10"),
    "fail": ("#fbdde2", "#b03a52"), "unknown": ("#e9e6f1", "#6c6783"),
    "hero_ok": "linear-gradient(135deg, #e3f6ec, #ece8fa)",
    "hero_warn": "linear-gradient(135deg, #fdf0dc, #ece8fa)",
    "hero_fail": "linear-gradient(135deg, #fbe2e6, #ece8fa)",
    "code_bg": "#f1eef8",
}
DARK = {
    "window": "#1d1b22", "view": "#26232d", "card": "#2b2833", "sidebar": "#221f28",
    "accent": "#b3a6ec", "accent_fg": "#1d1b22", "muted": "#a9a3bb", "border": "rgba(255,255,255,0.07)",
    "ok": ("#203b30", "#a6e3c4"), "warn": ("#41321f", "#f3cc96"),
    "fail": ("#45252c", "#f5a9b6"), "unknown": ("#322f3b", "#bcb6cc"),
    "hero_ok": "linear-gradient(135deg, #203a30, #2c2740)",
    "hero_warn": "linear-gradient(135deg, #3f3120, #2c2740)",
    "hero_fail": "linear-gradient(135deg, #43242b, #2c2740)",
    "code_bg": "#1f1d25",
}


def css(p: dict) -> str:
    status_rules = "\n".join(f"""
.chip.{s} {{ background: {bg}; color: {fg}; }}
.stat.{s} {{ background: {bg}; }}
.stat.{s} .stat-number, .stat.{s} .stat-label {{ color: {fg}; }}
.dot.{s} {{ background: {fg}; }}
image.status-{s} {{ color: {fg}; }}
""" for s, (bg, fg) in ((k, p[k]) for k in ("ok", "warn", "fail", "unknown")))
    return f"""
:root {{
  --accent-bg-color: {p['accent']};
  --accent-fg-color: {p['accent_fg']};
  --accent-color: {p['accent']};
  --window-bg-color: {p['window']};
  --view-bg-color: {p['view']};
  --card-bg-color: {p['card']};
  --sidebar-bg-color: {p['sidebar']};
  --headerbar-bg-color: {p['window']};
  --dialog-bg-color: {p['view']};
}}
{status_rules}
.chip {{ border-radius: 999px; padding: 6px; min-width: 20px; min-height: 20px; }}
.dot {{ border-radius: 999px; min-width: 9px; min-height: 9px; }}
.stat {{ border-radius: 18px; padding: 16px 18px; }}
.stat-number {{ font-size: 30px; font-weight: 800; }}
.stat-label {{ font-size: 13px; font-weight: 600; }}
.hero {{ border-radius: 22px; padding: 26px 28px; border: 1px solid {p['border']}; }}
.hero.ok {{ background-image: {p['hero_ok']}; }}
.hero.warn {{ background-image: {p['hero_warn']}; }}
.hero.fail {{ background-image: {p['hero_fail']}; }}
.hero-title {{ font-size: 24px; font-weight: 800; }}
.hero-sub, .muted {{ color: {p['muted']}; }}
.hero-icon {{ border-radius: 999px; padding: 14px; }}
.code {{ font-family: monospace; background: {p['code_bg']}; border-radius: 10px; padding: 8px 12px; }}
.detail {{ padding: 10px 14px 14px 14px; }}
.detail-title {{ font-weight: 700; font-size: 12px; color: {p['muted']}; }}
.error-box {{ background: {p['fail'][0]}; color: {p['fail'][1]}; border-radius: 10px; padding: 8px 12px; }}
.fix-banner {{ border-radius: 16px; padding: 14px 18px; background: {p['code_bg']}; border: 1px solid {p['border']}; }}
.log {{ font-family: monospace; font-size: 12px; }}
.sidebar-count {{ font-size: 12px; font-weight: 700; color: {p['muted']}; }}
"""
