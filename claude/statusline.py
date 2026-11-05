#!/usr/bin/env python3
"""Claude Code status for the tmux status bar.

Two modes:
  statusline.py --quiet    Registered as Claude Code's statusLine command. Reads the
                           payload JSON from stdin, saves it per tmux pane, prints
                           nothing (so no bar shows inside the Claude UI).
  statusline.py --tmux ID [WIDTH]
                           Called from tmux status-left via #(...). Renders the saved
                           payload of pane ID in tmux style syntax, or nothing if
                           that pane has no recent Claude session.

Segments are dropped (lowest priority first) when there isn't enough width.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

SEP = ""
THIN = ""
BRANCH = ""
FILLED, EMPTY = "▰", "▱"
BAR_WIDTH = 6
GIT_TTL = 5  # seconds
STALE_AFTER = 120  # seconds before a pane's saved payload is ignored by tmux
CACHE_DIR = os.path.expanduser("~/.cache/claude-statusline")

# word color matches the dark text of the tmux status-left segments
TEXT = "#1d2021"
MAGENTA, CYAN, GREEN, YELLOW, ORANGE, RED = "magenta", "cyan", "green", "yellow", "colour208", "red"
MODEL_COLORS = {"haiku": YELLOW, "sonnet": ORANGE, "opus": RED}


def model_color(model):
    ident = f"{model.get('id', '')} {model.get('display_name', '')}".lower()
    return next((c for name, c in MODEL_COLORS.items() if name in ident), MAGENTA)


def level_color(pct):
    """green -> yellow -> orange -> red as usage grows."""
    if pct < 50:
        return GREEN
    if pct < 75:
        return YELLOW
    if pct < 90:
        return ORANGE
    return RED


def bar(pct):
    filled = max(0, min(BAR_WIDTH, round(pct / 100 * BAR_WIDTH)))
    return FILLED * filled + EMPTY * (BAR_WIDTH - filled)


def fmt_remaining(resets_at):
    secs = int(resets_at - time.time())
    if secs <= 0:
        return "now"
    h, m = divmod(secs // 60, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


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
    five = (data.get("rate_limits") or {}).get("five_hour") or {}

    name = model.get("display_name") or "claude"
    segs = [(0, f" {name if not effort else f'{name} · {effort}'} ", model_color(model), True)]

    parts = [p for p in cwd.split("/") if p]
    segs.append((2, f" {parts[-1] if parts else '/'} ", CYAN, True))
    git = git_info(cwd)
    if git:
        branch, dirty = git
        segs.append((2, f" {BRANCH} {branch}{' ±' if dirty else ''} ", YELLOW if dirty else GREEN, False))

    if ctx is not None:
        segs.append((1, f" context {bar(ctx)} {ctx:.0f}% ", level_color(ctx), False))

    if five.get("used_percentage") is not None:
        p = five["used_percentage"]
        reset = f" ↻{fmt_remaining(five['resets_at'])}" if five.get("resets_at") else ""
        segs.append((3, f" 5h {bar(p)} {p:.0f}%{reset} ", level_color(p), False))
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
    # arrow out of the host segment of tmux status-left (#3c3836 background)
    line = style("#3c3836", segs[0][2]) + SEP
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


def pane_cache(pane):
    return os.path.join(CACHE_DIR, pane.lstrip("%") + ".json")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--quiet"
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
