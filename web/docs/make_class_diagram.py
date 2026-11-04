"""Draw the UML class diagram of subsystem 4.

Run it from the web folder with:  python docs/make_class_diagram.py
It needs matplotlib, which is not a dependency of the app itself.
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

DARK = "#1A1A19"
GREEN = "#1B7F3B"
LINE = "#7F9A6E"
HEAD = "#E7EFDF"
EXT_HEAD = "#ECECE8"
EXT_EDGE = "#9A9A93"
MUTED = "#6B6B66"

HEAD_H = 4.8
ROW = 2.9
PAD = 1.1
GAP = 1.0
TAG_H = 2.4
FS_NAME = 10.0
FS_ROW = 7.6
FS_TAG = 6.8

fig, ax = plt.subplots(figsize=(13.5, 8.2), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def draw(x, y_top, w, name, attrs=(), methods=(), external=False, stereotype=None):
    """Draw one class box and return where its edges are."""
    separator = GAP if attrs and methods else 0
    height = HEAD_H + PAD + ROW * len(attrs) + separator + ROW * len(methods) + PAD
    height += TAG_H if stereotype else 0
    bottom = y_top - height
    edge = EXT_EDGE if external else GREEN

    ax.add_patch(FancyBboxPatch(
        (x, bottom), w, height, boxstyle="round,pad=0,rounding_size=0.7",
        linewidth=1.2, edgecolor=edge, facecolor="white",
        linestyle="dashed" if external else "solid", zorder=2))

    head_top = y_top
    if stereotype:
        ax.text(x + w / 2, y_top - 1.3, stereotype, ha="center", va="center",
                fontsize=FS_TAG, style="italic", color=MUTED, zorder=5)
        head_top = y_top - TAG_H

    ax.add_patch(Rectangle((x + 0.08, head_top - HEAD_H), w - 0.16, HEAD_H - 0.22, linewidth=0,
                           facecolor=EXT_HEAD if external else HEAD, zorder=3))
    ax.plot([x, x + w], [head_top - HEAD_H] * 2, color=edge, lw=1.0, zorder=4)
    ax.text(x + w / 2, head_top - HEAD_H / 2 + 0.15, name, ha="center", va="center",
            fontsize=FS_NAME, fontweight="bold", color=DARK, zorder=5)

    y = head_top - HEAD_H - PAD - ROW / 2
    for attr in attrs:
        ax.text(x + 1.0, y, attr, ha="left", va="center", fontsize=FS_ROW,
                family="monospace", color=DARK, zorder=5)
        y -= ROW
    if attrs and methods:
        line_y = y + ROW / 2 - GAP / 2
        ax.plot([x, x + w], [line_y, line_y], color=LINE, lw=0.8, zorder=4)
        y -= GAP
    for method in methods:
        ax.text(x + 1.0, y, method, ha="left", va="center", fontsize=FS_ROW,
                family="monospace", color=GREEN, zorder=5)
        y -= ROW

    return {"x": x, "w": w, "top": y_top, "bottom": bottom, "midx": x + w / 2}


def label(x, y, text, ha="left"):
    """Write the name of a relationship."""
    ax.text(x, y, text, ha=ha, va="center", fontsize=FS_TAG, style="italic", color=MUTED, zorder=5)


def inherits(child, parent):
    """Solid line with an arrow head: child is a kind of parent."""
    ax.add_patch(FancyArrowPatch(
        (child["midx"], child["top"]), (parent["midx"], parent["bottom"]),
        arrowstyle="-|>", mutation_scale=11, linewidth=1.1, color=GREEN,
        shrinkA=0, shrinkB=0, zorder=1))


def composition(start, end):
    """Solid line with a filled diamond at the owner: the owner holds the other class."""
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-", linewidth=1.1, color=LINE,
                                 shrinkA=0, shrinkB=0, zorder=1))
    ax.plot(*start, marker="D", markersize=5, color=LINE, zorder=6)


def uses(start, end):
    """Dashed arrow: one class creates or uses the other."""
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=9, linewidth=1.0,
                                 color=LINE, linestyle="dashed", shrinkA=0, shrinkB=0, zorder=1))


# --- the pages ---------------------------------------------------------------------------
base_page = draw(16.0, 97.0, 30.0, "BasePage",
                 ["+ title: str", "+ icon: str", "# services: AppServices"],
                 ["+ label: str  «property»", "+ render(region_code): None"],
                 stereotype="«abstract»")

scan_page = draw(1.0, 66.0, 25.0, "ScanPage", ["+ workflow: ScanWorkflow"],
                 ["+ render(region_code): None", "- _scan_once(photo, region)",
                  "- _show(outcome): None", "- _show_top3(outcome): None"])
dashboard_page = draw(28.0, 66.0, 17.0, "DashboardPage", [], ["+ render(region_code)"])
about_page = draw(46.0, 66.0, 17.0, "AboutPage", [], ["+ render(region_code)"])

inherits(scan_page, base_page)
inherits(dashboard_page, base_page)
inherits(about_page, base_page)
label(47.0, 69.0, "inherits")

# --- one scan ----------------------------------------------------------------------------
workflow = draw(1.0, 35.0, 32.0, "ScanWorkflow", ["- services: AppServices"],
                ["+ run(image, region): ScanOutcome",
                 "+ for_region(outcome, region): ScanOutcome",
                 "- _save(result, region): int | None"])
outcome = draw(38.0, 35.0, 25.0, "ScanOutcome",
               ["+ result: ClassificationResult", "+ explanation: Explanation",
                "+ saved_id: int | None"],
               ["+ is_confident: bool  «property»", "+ was_saved: bool  «property»"],
               stereotype="«frozen dataclass»")

composition((scan_page["midx"] - 3.0, scan_page["bottom"]), (scan_page["midx"] - 3.0, workflow["top"]))
label(scan_page["midx"] - 2.0, (scan_page["bottom"] + workflow["top"]) / 2, "holds")
uses((workflow["x"] + workflow["w"], 25.0), (outcome["x"], 25.0))
label(35.5, 27.0, "creates", ha="center")

# --- what the pages and the workflow work with --------------------------------------------
services = draw(67.0, 97.0, 32.0, "AppServices",
                ["+ classifier: ClassificationEngine", "+ dal: DataAccessLayer",
                 "+ rules: RuleEngine", "+ coach: CoachService",
                 "+ analytics: AnalyticsService"],
                ["+ regions(): list"],
                stereotype="«frozen dataclass»")
composition((base_page["x"] + base_page["w"], 84.0), (services["x"], 84.0))
label(56.5, 86.0, "holds", ha="center")

# --- the other three subsystems -----------------------------------------------------------
ax.add_patch(FancyBboxPatch((67.0, 38.5), 32.0, 26.5, boxstyle="round,pad=0,rounding_size=0.7",
                            linewidth=1.0, edgecolor=EXT_EDGE, facecolor="#FAFAF8",
                            linestyle="dotted", zorder=0))
label(83.0, 63.2, "from Subsystems 1, 2 and 3", ha="center")
draw(68.0, 61.5, 30.0, "ClassificationEngine", external=True)
draw(68.0, 54.0, 14.5, "RuleEngine", external=True)
draw(83.5, 54.0, 14.5, "DataAccessLayer", external=True)
draw(68.0, 46.5, 14.5, "CoachService", external=True)
draw(83.5, 46.5, 14.5, "AnalyticsService", external=True)
composition((services["midx"], services["bottom"]), (services["midx"], 65.0))
label(services["midx"] + 1.0, (services["bottom"] + 65.0) / 2, "holds")

# --- settings and errors ------------------------------------------------------------------
draw(67.0, 36.0, 14.0, "WebConfig",
     ["+ database_url", "+ default_region", "+ title"], ["+ from_env()"],
     stereotype="«frozen dataclass»")
web_error = draw(82.0, 36.0, 17.0, "WebError", [], [], stereotype="«exception»")
startup_error = draw(82.0, 22.0, 17.0, "ServiceStartupError", [], [], stereotype="«exception»")
inherits(startup_error, web_error)

ax.text(50, 3.0,
        "Subsystem 4: Web Interface & Deployment.   Dashed boxes belong to the other subsystems.   "
        "build_services(config) creates AppServices.",
        ha="center", va="center", fontsize=8, style="italic", color=MUTED)

output = pathlib.Path(__file__).with_name("class_diagram.png")
fig.savefig(str(output), facecolor="white", bbox_inches="tight", pad_inches=0.1)
print("saved", output.name)
