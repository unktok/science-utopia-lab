"""Reproducible research-program schematic; no curves are empirical data."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
C = dict(ink='#253346', muted='#637285', line='#CAD4DF', blue='#3269A8',
    blue_bg='#EDF4FB', teal='#187F79', teal_bg='#EAF5F1', amber='#A56A24',
    amber_bg='#FCF4E7', purple='#7762A1', purple_bg='#F3EFF8')


def make_figure(output=None):
    output = Path(output or ROOT / 'paper/figures/program-concept/science-system-design-program')
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'svg.fonttype': 'none',
        'svg.hashsalt': 'science-utopia-lab-research-program-v1'})
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    fig.subplots_adjust(left=.008, right=.992, bottom=.015, top=.985)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')

    def text(x, y, s, size=8, color=None, weight='normal', ha='center', **kw):
        return ax.text(x, y, s, fontsize=size, color=color or C['ink'], weight=weight, ha=ha, va='center', **kw)

    def panel(x, y, w, h, fill, edge=None):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.006,rounding_size=0.013', fc=fill, ec=edge or C['line'], lw=.8))

    def arrow(points, color=None, dashed=False, lw=1.1, head=7):
        color = color or C['muted']
        xx, yy = zip(*points)
        if len(points) > 2:
            ax.plot(xx[:-1], yy[:-1], color=color, lw=lw, ls=(0, (3, 2)) if dashed else '-', zorder=3)
        ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle='-|>', mutation_scale=head,
            lw=lw, color=color, linestyle=(0, (3, 2)) if dashed else '-', zorder=3))

    def edge(a, b, color=None, dashed=False):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color or C['line'], lw=.85, ls=(0, (3, 2)) if dashed else '-', zorder=2)

    def node(x, y, dashed=False):
        ax.add_patch(Circle((x, y), .014, fc='white', ec=C['teal'], lw=1.1, linestyle=(0, (2, 1.7)) if dashed else '-', zorder=4))

    def person(x, y, color):
        ax.add_patch(Circle((x, y+.010), .009, fc=color, ec='none', zorder=4))
        ax.add_patch(FancyBboxPatch((x-.011, y-.017), .022, .019, boxstyle='round,pad=0,rounding_size=0.005', fc=color, ec='none', zorder=4))

    text(.035, .972, 'WHAT CAN CHANGE?', 7.7, C['teal'], 'bold', ha='left')
    text(.965, .972, 'Composable design freedoms', 7.7, C['muted'], ha='right')
    ax.plot([.035, .965], [.944, .944], color=C['line'], lw=.8)
    for x, label in [(.102, 'Parameters'), (.317, 'Algorithms / source'), (.578, 'Mechanisms / protocols'), (.851, 'Wiring / order / topology')]:
        text(x, .911, label, 7.8)
    for x in (.203, .442, .723):
        arrow([(x-.012, .911), (x+.012, .911)], C['teal'], lw=.8, head=6)

    text(.119, .814, 'Choose the objective', 8.2, weight='bold')
    text(.119, .765, 'Explicit, replaceable\nresearch objectives', 7.5, C['muted'])
    for yy, label, color, shift in [(.687, '$L_A$', C['blue'], -.008), (.622, '$L_B$', C['teal'], .018), (.557, '$L_C$', C['purple'], -.025)]:
        text(.046, yy, label, 10, color)
        xs = np.linspace(.079, .190, 60)
        ax.plot(xs, yy-.013+.020*np.minimum(((xs-(.132+shift))/.07)**2, 1.4), color=color, lw=1.35)
    text(.116, .487, 'Different objectives\ncan favor different systems', 7.5, C['muted'])

    panel(.313, .575, .382, .255, C['teal_bg'], '#B7D7D0')
    text(.504, .799, 'Design the scientific system', 9.5, weight='bold')
    text(.504, .762, 'Executable rules and institutional flows', 7.6, C['muted'])
    points = [(.370, .681), (.454, .713), (.539, .670), (.623, .713), (.454, .621)]
    for a, b in [(0, 1), (1, 2), (2, 3), (0, 4), (4, 2), (1, 4)]:
        edge(points[a], points[b], '#77ADA2')
    for xy in points:
        node(*xy)
    node(.623, .622, dashed=True)
    edge(points[2], (.623, .622), C['teal'], dashed=True)
    text(.645, .647, '…', 12, C['teal'])
    arrow([(.343, .573), (.343, .513)], C['teal'])
    arrow([(.665, .513), (.665, .573)], C['teal'])
    text(.504, .545, 'Institutions ↔ scientific activity', 7.6, C['muted'])

    panel(.313, .272, .382, .238, C['blue_bg'], '#B9CEE4')
    text(.504, .479, 'Execute the researcher ecosystem', 8.4, weight='bold')
    people = [(.361, .416), (.415, .394), (.471, .426), (.532, .396), (.591, .424), (.648, .393)]
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 2)]:
        edge(people[a], people[b], '#B4C9DE')
    for i, xy in enumerate(people):
        person(*xy, C['blue'] if i % 2 == 0 else '#6C91B7')
    for x, y in [(.393, .336), (.477, .332), (.563, .339)]:
        ax.add_patch(Rectangle((x, y), .018, .026, fc='white', ec=C['muted'], lw=.65, zorder=4))
        for k in range(3):
            ax.plot([x+.003, x+.015], [y+.019-.005*k]*2, color=C['line'], lw=.7, zorder=5)
    text(.504, .303, 'Research • artifacts • exchange • resources', 7.6, C['muted'])
    text(.504, .233, 'Original fixed-LLM world: minimum instance,\nopen to richer scientific systems', 7.7, C['blue'])

    arrow([(.702, .398), (.774, .398)], C['blue'])
    text(.877, .455, 'Observe outcomes', 9, weight='bold')
    text(.877, .398, 'Trajectories, outputs,\nparticipation, costs, …', 7.6, C['muted'])
    arrow([(.877, .358), (.877, .292)])
    panel(.770, .175, .214, .109, '#F8FAFC')
    text(.877, .260, 'Independent evaluation', 7.2, weight='bold')
    text(.877, .215, 'Held-out seeds\nReporting metrics', 7.2, C['muted'])

    panel(.782, .621, .190, .205, C['purple_bg'], '#D4C9E3')
    ax.add_patch(Rectangle((.806, .691), .141, .101, fc='white', ec='#B4A5C9', lw=.7))
    for x, h in [(.817, .035), (.853, .054), (.896, .042)]:
        ax.add_patch(Rectangle((x, .704), .024, h, fc='#D7CEE5', ec='none'))
    person(.840, .722, C['purple'])
    person(.890, .719, C['purple'])
    text(.877, .665, 'Game-like interface', 8, weight='bold')
    text(.877, .636, 'Inspect • edit • replay', 7.3, C['muted'])
    arrow([(.704, .461), (.755, .461), (.755, .725), (.777, .725)], C['purple'], lw=.9)

    panel(.313, .067, .382, .111, C['amber_bg'], '#E5CFAE')
    text(.504, .153, 'HOW TO SEARCH?', 7.6, C['amber'], 'bold')
    text(.504, .119, 'Black-box     Gradients     Hybrid', 8.5, weight='bold')
    text(.504, .087, 'Whole-world backprop: research target', 7.3, C['muted'])
    arrow([(.116, .446), (.116, .121), (.307, .121)], C['amber'])
    text(.128, .303, 'Declared\nloss', 7.8, C['amber'], ha='left')
    arrow([(.814, .350), (.737, .350), (.737, .122), (.702, .122)], C['amber'])
    text(.750, .296, 'Score', 7.5, C['amber'], rotation=90)
    arrow([(.313, .151), (.278, .151), (.278, .720), (.307, .720)], C['amber'])
    text(.262, .436, 'Propose → execute → measure → revise', 7.4, C['amber'], rotation=90)
    arrow([(.695, .418), (.716, .418), (.716, .635), (.695, .635)], C['purple'], dashed=True, lw=.85, head=6)
    ax.plot([.035, .075], [.027, .027], color=C['muted'], lw=1)
    text(.085, .027, 'Executable loop / interface', 6.9, C['muted'], ha='left')
    ax.plot([.420, .460], [.027, .027], color=C['purple'], lw=1, ls=(0, (3, 2)))
    text(.470, .027, 'Extension / internal redesign', 6.9, C['muted'], ha='left')
    text(.968, .027, 'Conceptual', 6.8, C['muted'], ha='right')

    fig.savefig(output.with_suffix('.pdf'), metadata={'Title': 'Scientific systems as objects of design',
        'Subject': 'Research-program concept, not empirical results or completion claim', 'Creator': 'Science Utopia Lab',
        'CreationDate': None, 'ModDate': None})
    fig.savefig(output.with_suffix('.png'), dpi=230)
    fig.savefig(output.with_suffix('.svg'), metadata={'Date': None})
    plt.close(fig)
    return output


if __name__ == '__main__':
    print(make_figure())
