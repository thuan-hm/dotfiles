#!/usr/bin/env python3
"""Claude Code status for the tmux status bar.

Two modes:
  statusline.py --quiet    Registered as Claude Code's statusLine command. Reads the
                           payload JSON from stdin, saves it per tmux pane, prints
                           nothing (so no bar shows inside the Claude UI).
  statusline.py --sys      Called from tmux status-right. Prints CPU, RAM, disk and
                           battery segments (right-aligned powerline).
  statusline.py --tmux ID [WIDTH]
                           Called from tmux status-left via #(...). Renders the saved
                           payload of pane ID in tmux style syntax, or nothing if
                           that pane has no recent Claude session.

Segments are dropped (lowest priority first) when there isn't enough width.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

SEP = ""
THIN = ""
BRANCH = ""
FILLED, EMPTY = "▰", "▱"
BAR_WIDTH = 6
GIT_TTL = 5  # seconds
STALE_AFTER = 120  # seconds before a pane's saved payload is ignored by tmux
SYS_TTL = 5  # seconds
CACHE_DIR = os.path.expanduser("~/.cache/claude-statusline")

# Nerd Font icons
ICON_CPU, ICON_RAM, ICON_DISK, ICON_BOLT = "\U000f04c5", "\U000f035b", "\uf0a0", "\uf0e7"
ICON_BATT = ["\uf244", "\uf243", "\uf242", "\uf241", "\uf240"]  # empty .. full
SEP_L, THIN_L = "\ue0b2", "\ue0b3"

# Tokyo Night; text is the terminal background, like the tmux status-left segments
TEXT = "#1a1b26"
LEFT_BG = "#292e42"  # background strip the tmux status-left gradient ends on
PURPLE, GREEN, YELLOW, ORANGE, RED = "#bb9af7", "#9ece6a", "#e0af68", "#ff9e64", "#f7768e"
MODEL_COLORS = {"haiku": YELLOW, "sonnet": ORANGE, "opus": RED}


def model_color(model):
    ident = f"{model.get('id', '')} {model.get('display_name', '')}".lower()
    return next((c for name, c in MODEL_COLORS.items() if name in ident), PURPLE)


# usage scale (percent, color): green when low, red when high, blended in between
LEVEL_STOPS = [
    (0, "#9ece6a"),   # green
    (25, "#b5c565"),  # yellow-green
    (45, "#e0af68"),  # yellow
    (65, "#ff9e64"),  # orange
    (85, "#f7768e"),  # red
    (100, "#db4b4b"), # deep red
]


def level_color(pct):
    """Blend between the stops above so the color tracks usage smoothly."""
    pct = max(0.0, min(100.0, pct))
    for (lo, a), (hi, b) in zip(LEVEL_STOPS, LEVEL_STOPS[1:]):
        if pct <= hi:
            t = (pct - lo) / (hi - lo)
            rgb = [round(int(a[k:k + 2], 16) + t * (int(b[k:k + 2], 16) - int(a[k:k + 2], 16))) for k in (1, 3, 5)]
            return "#%02x%02x%02x" % tuple(rgb)
    return LEVEL_STOPS[-1][1]


def bar(pct):
    filled = max(0, min(BAR_WIDTH, round(pct / 100 * BAR_WIDTH)))
    return FILLED * filled + EMPTY * (BAR_WIDTH - filled)


def fmt_reset(resets_at):
    """Local wall-clock time of the reset: 18:30 today, or 'Mon 09:00' on another day."""
    when = datetime.fromtimestamp(resets_at)
    same_day = when.date() == datetime.now().date()
    return when.strftime("%H:%M" if same_day else "%a %H:%M")


def git_info(cwd):
    """Return (branch, dirty) or None; cached briefly because tmux re-renders often."""
    cache = os.path.join(
        tempfile.gettempdir(),
        f"cc-statusline-git-{hashlib.md5(cwd.encode()).hexdigest()[:10]}.json",
    )
    try:
        if time.time() - os.path.getmtime(cache) < GIT_TTL:
            with open(cache) as f:
                cached = json.load(f)
            return tuple(cached) if cached else None
    except (OSError, ValueError):
        pass
    result = None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "--no-optional-locks", "status", "--porcelain", "-b"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode == 0:
            lines = out.stdout.splitlines()
            head = lines[0][3:] if lines else ""
            name = head.split("...")[0].split(" ")[0]
            if name.startswith("No commits yet on "):
                name = name.rsplit(" ", 1)[-1]
            result = (name, len(lines) > 1)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        with open(cache, "w") as f:
            json.dump(result, f)
    except OSError:
        pass
    return result


def build_segments(data):
    """Return [(priority, text, bg, bold)]; lower priority number = kept longest."""
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    model = data.get("model") or {}
    effort = (data.get("effort") or {}).get("level") or os.environ.get("CLAUDE_EFFORT")
    ctx = (data.get("context_window") or {}).get("used_percentage")
    limits = data.get("rate_limits") or {}

    name = model.get("display_name") or "claude"
    segs = [(0, f" {name if not effort else f'{name} · {effort}'} ", model_color(model), True)]

    parts = [p for p in cwd.split("/") if p]
    segs.append((2, f" {parts[-1] if parts else '/'} ", PURPLE, True))
    git = git_info(cwd)
    if git:
        branch, dirty = git
        segs.append((2, f" {BRANCH} {branch}{' ±' if dirty else ''} ", YELLOW if dirty else GREEN, False))

    if ctx is not None:
        segs.append((1, f" context {bar(ctx)} {ctx:.0f}% ", level_color(ctx), False))

    for priority, key, label in ((3, "five_hour", "5h"), (4, "seven_day", "7d")):
        window = limits.get(key) or {}
        p = window.get("used_percentage")
        if p is None:
            continue
        reset = f" ↻ {fmt_reset(window['resets_at'])}" if window.get("resets_at") else ""
        segs.append((priority, f" {label} {bar(p)} {p:.0f}%{reset} ", level_color(p), False))
    return segs


def fit(segs, budget):
    keep = list(segs)
    while len(keep) > 1 and sum(len(s[1]) + 1 for s in keep) > budget:
        keep.remove(max(keep, key=lambda s: s[0]))
    return keep


def style(fg=None, bg=None, bold=None):
    return "#[" + ",".join(
        x for x in (
            fg and f"fg={fg}",
            bg and f"bg={bg}",
            {True: "bold", False: "nobold"}.get(bold),
        ) if x
    ) + "]"


def render(segs):
    """Join segments with powerline arrows in tmux #[...] style syntax."""
    # arrow out of the host segment of tmux status-left (LEFT_BG background)
    line = style(LEFT_BG, segs[0][2]) + SEP
    for i, (_, text, bg, bold) in enumerate(segs):
        line += style(TEXT, bg, bold) + text.replace("#", "##")
        nxt = segs[i + 1][2] if i + 1 < len(segs) else None
        if nxt == bg:
            line += style(TEXT, bg, False) + THIN
        elif nxt is not None:
            line += style(bg, nxt, False) + SEP
        else:
            line += "#[default]" + style(bg, None, False) + SEP
    return line + "#[default]"


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_percent():
    # second sample of top is the delta over the interval; the first is since boot
    out = run(["top", "-l", "2", "-n", "0", "-s", "1"])
    m = re.findall(r"CPU usage:.*?([\d.]+)% idle", out)
    return 100 - float(m[-1]) if m else None


def ram_percent():
    total = run(["sysctl", "-n", "hw.memsize"]).strip()
    out = run(["vm_stat"])
    size = re.search(r"page size of (\d+)", out)
    if not (total.isdigit() and size):
        return None
    pages = lambda label: int((re.search(rf"{label}:\s+(\d+)", out) or [0, 0])[1])
    used = pages("Pages active") + pages("Pages wired down") + pages("Pages occupied by compressor")
    return min(100.0, used * int(size[1]) / int(total) * 100)


def disk_percent():
    path = "/System/Volumes/Data" if os.path.exists("/System/Volumes/Data") else "/"
    u = shutil.disk_usage(path)
    return u.used / u.total * 100


def battery():
    """Return (percent, charging) or None on a machine without a battery."""
    out = run(["pmset", "-g", "batt"])
    m = re.search(r"(\d+)%;\s*([^;]+);", out)
    if not m:
        return None
    return float(m[1]), m[2].strip() in ("charging", "finishing charge", "charged")


def sys_stats():
    """CPU/RAM/disk/battery, cached because top takes ~1s and tmux re-renders often."""
    path = os.path.join(CACHE_DIR, "sys.json")
    try:
        if time.time() - os.path.getmtime(path) < SYS_TTL:
            with open(path) as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    stats = {"cpu": cpu_percent(), "ram": ram_percent(), "disk": disk_percent(), "batt": battery()}
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(stats, f)
        os.replace(tmp, path)
    except OSError:
        pass
    return stats


def sys_segments(stats):
    segs = []
    for icon, label, key in ((ICON_CPU, "CPU", "cpu"), (ICON_RAM, "RAM", "ram"), (ICON_DISK, "SSD", "disk")):
        if stats.get(key) is not None:
            segs.append((0, f" {icon} {label} {stats[key]:.0f}% ", level_color(stats[key]), False))
    if stats.get("batt"):
        pct, charging = stats["batt"]
        icon = ICON_BOLT if charging else ICON_BATT[min(4, int(pct // 20))]
        # battery is the inverse: low is bad
        segs.append((0, f" {icon} {pct:.0f}% ", level_color(100 - pct), False))
    return segs


def render_right(segs):
    """Right-aligned powerline: arrows point left, each coming out of the previous bg."""
    line, prev = "", None
    for _, text, bg, bold in segs:
        if prev == bg:
            line += style(TEXT, bg, False) + THIN_L
        else:
            line += style(bg, prev or "default", False) + SEP_L
        line += style(TEXT, bg, bold) + text
        prev = bg
    return line + "#[default]"


def pane_cache(pane):
    return os.path.join(CACHE_DIR, pane.lstrip("%") + ".json")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--quiet"
    if mode == "--sys":
        segs = sys_segments(sys_stats())
        if segs:
            print(render_right(segs))
        return
    if mode == "--tmux":
        pane = sys.argv[2] if len(sys.argv) > 2 else ""
        width = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 0
        try:
            path = pane_cache(pane)
            if time.time() - os.path.getmtime(path) > STALE_AFTER:
                return
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        segs = build_segments(data)
        if width:
            segs = fit(segs, width - 45)  # leave room for the session/window/host segments
        print(render(segs))
        return

    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    pane = os.environ.get("TMUX_PANE")
    if pane:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = pane_cache(pane) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, pane_cache(pane))
        except OSError:
            pass
    print()


if __name__ == "__main__":
    main()
