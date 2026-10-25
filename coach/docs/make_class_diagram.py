"""Draw the UML class diagram of subsystem 3.

Run it with:  python docs/make_class_diagram.py
It needs matplotlib, which is not a dependency of the subsystem itself.
"""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

W, H = 13.5, 8.2
DARK = "#1A1A19"
GREEN = "#1B7F3B"
LINE = "#9FB58F"
BG = "#FFFFFF"
HEAD = "#E7EFDF"
EXT_HEAD = "#ECECE8"
EXT_EDGE = "#9A9A93"
MUTED = "#6B6B66"

fig, ax = plt.subplots(figsize=(W, H), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.patch.set_facecolor(BG)

HEAD_H = 4.8
ROW = 2.9
PAD = 1.1
GAP = 1.0
FS_NAME = 10.0
FS_ROW = 7.6
FS_TAG = 6.8


def draw(x, y_top, w, name, attrs, methods, external=False, stereotype=None):
    body = PAD + ROW * len(attrs) + (GAP if attrs and methods else 0) + ROW * len(methods) + PAD
    h = HEAD_H + body + (2.4 if stereotype else 0)
    y = y_top - h

    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.7",
        linewidth=1.2, edgecolor=EXT_EDGE if external else GREEN,
        facecolor=BG, linestyle="dashed" if external else "solid", zorder=2))

    head_top = y_top
    if stereotype:
        ax.text(x + w / 2, y_top - 1.3, stereotype, ha="center", va="center",
                fontsize=FS_TAG, style="italic", color=MUTED, zorder=5)
        head_top = y_top - 2.4

    ax.add_patch(plt.Rectangle(
        (x + 0.08, head_top - HEAD_H), w - 0.16, HEAD_H - 0.22,
        linewidth=0, facecolor=EXT_HEAD if external else HEAD, zorder=3))
    ax.plot([x, x + w], [head_top - HEAD_H, head_top - HEAD_H],
            color=EXT_EDGE if external else GREEN, lw=1.0, zorder=4)
    ax.text(x + w / 2, head_top - HEAD_H / 2 + 0.15, name, ha="center", va="center",
            fontsize=FS_NAME, fontweight="bold", color=DARK, zorder=5)

    ty = head_top - HEAD_H - PAD - ROW / 2
    for a in attrs:
        ax.text(x + 1.0, ty, a, ha="left", va="center", fontsize=FS_ROW,
                family="monospace", color=DARK, zorder=5)
        ty -= ROW

    if attrs and methods:
        sep = ty + ROW / 2 - 0.35
        ax.plot([x, x + w], [sep, sep], color=LINE, lw=0.8, zorder=4)
        ty = sep - GAP - ROW / 2 + 0.35

    for m in methods:
        ax.text(x + 1.0, ty, m, ha="left", va="center", fontsize=FS_ROW,
                family="monospace", color=MUTED if external else GREEN, zorder=5)
        ty -= ROW

    return {"x": x, "w": w, "top": y_top, "bottom": y, "midx": x + w / 2, "midy": y + h / 2}


def uses(p0, p1, label="", dx=0.0, dy=1.0, ha="center", va="bottom"):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=9, linewidth=1.0,
        color=LINE, linestyle="dashed", shrinkA=0, shrinkB=0, zorder=1))
    if label:
        ax.text((p0[0] + p1[0]) / 2 + dx, (p0[1] + p1[1]) / 2 + dy, label,
                ha=ha, va=va, fontsize=FS_TAG, style="italic",
                color=MUTED, zorder=5)


def inherits(child, parent):
    ax.add_patch(FancyArrowPatch(
        (child["midx"], child["top"]), (parent["midx"], parent["bottom"]),
        arrowstyle="-|>", mutation_scale=11, linewidth=1.1,
        color=GREEN, shrinkA=0, shrinkB=0, zorder=1))


# --- column A: the two services and what they depend on outside ----------------
coach = draw(1.0, 97.0, 31.0, "CoachService",
             ["- rules: RuleEngine", "- cache: BaseCache",
              "- explainer: BaseExplainer", "- fallback: BaseExplainer"],
             ["+ explain(item, category, region): Explanation",
              "+ explain_result(result, region): Explanation",
              "- generate(item, rule): tuple"])

rule_engine = draw(1.0, 64.0, 31.0, "RuleEngine", [],
                   ["+ get_rule(category, region): Rule"],
                   external=True, stereotype="«from Subsystem 2»")

analytics = draw(1.0, 47.0, 31.0, "AnalyticsService",
                 ["- dal: DataAccessLayer"],
                 ["+ frame(region, since, until): DataFrame",
                  "+ composition(region): dict",
                  "+ recycling_rate(region): float",
                  "+ trend(region, days): DataFrame",
                  "+ summary(region): Summary"])

dal = draw(1.0, 17.0, 31.0, "DataAccessLayer", [],
           ["+ get_results(region, since, until)"],
           external=True, stereotype="«from Subsystem 2»")

# --- column B: the two abstractions and their implementations -------------------
base_cache = draw(37.0, 97.0, 28.0, "BaseCache", [],
                  ["+ get(key): str | None", "+ set(key, text): None",
                   "+ clear(): None"], stereotype="«abstract»")

memory = draw(37.0, 74.0, 13.0, "MemoryCache", ["- store: dict"], [])
sqlite = draw(52.0, 74.0, 13.0, "SQLiteCache", ["- path: Path"], [])

base_expl = draw(37.0, 58.0, 28.0, "BaseExplainer", ["+ source: str"],
                 ["+ explain(item, rule): str", "+ is_available(): bool"],
                 stereotype="«abstract»")

template = draw(37.0, 34.0, 13.0, "TemplateExplainer", ["- language: str"], [])
llm = draw(52.0, 34.0, 13.0, "LanguageModelExpl.", ["- client", "- config"], [])

# --- column C: what crosses the boundary, and the settings ----------------------
explanation = draw(70.0, 97.0, 29.0, "Explanation",
                   ["+ text: str", "+ bin: str", "+ category: str",
                    "+ region_code: str", "+ source: str"], [])

summary = draw(70.0, 71.0, 29.0, "Summary",
               ["+ total_scans: int", "+ recycling_rate: float",
                "+ composition: dict", "+ average_confidence: float"], [])

client = draw(70.0, 48.0, 29.0, "OpenAIClient", ["- config: CoachConfig"],
              ["+ is_available(): bool", "+ send(prompt): str"])

config = draw(70.0, 27.0, 29.0, "CoachConfig",
              ["+ api_key: str", "+ model: str",
               "+ cache_path: str", "+ language: str"],
              ["+ from_env(): CoachConfig"])

# --- relationships ---------------------------------------------------------------
uses((coach["x"] + coach["w"], 85.0), (base_cache["x"], 88.0), "uses")
uses((coach["midx"], coach["bottom"]), (rule_engine["midx"], rule_engine["top"]),
     "asks for the rule", dx=1.2, dy=-0.6, ha="left", va="center")
uses((coach["x"] + coach["w"], 71.0), (base_expl["x"], 50.0), "uses")
uses((analytics["midx"], analytics["bottom"]), (dal["midx"], dal["top"]),
     "reads the scans", dx=1.2, dy=-0.6, ha="left", va="center")
uses((llm["x"] + llm["w"], 29.0), (client["x"], 34.0), "uses", dx=0.0, dy=1.2)

inherits(memory, base_cache)
inherits(sqlite, base_cache)
inherits(template, base_expl)
inherits(llm, base_expl)

ax.text(51.0, 76.2, "inherits", ha="center", fontsize=FS_TAG, style="italic", color=MUTED)
ax.text(51.0, 36.2, "inherits", ha="center", fontsize=FS_TAG, style="italic", color=MUTED)

ax.text(50, 1.0,
        "Subsystem 3 — AI Coach & Analytics.   Dashed boxes belong to Subsystem 2.",
        ha="center", va="center", fontsize=8, style="italic", color=MUTED)

fig.savefig(str(pathlib.Path(__file__).with_name("class_diagram.png")),
            facecolor=BG, bbox_inches="tight", pad_inches=0.1)
print("saved")
