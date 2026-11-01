"""Publication-native schematic; illustrations are not empirical data."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path as VectorPath
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
C = dict(ink='#253346', muted='#637285', line='#CBD5DF', blue='#3269A8',
    blue_bg='#EDF4FB', teal='#187F79', teal_bg='#EAF5F1', amber='#A56A24',
    amber_bg='#FCF4E7', purple='#7762A1')


@dataclass(frozen=True)
class Frame:
    x: float
    y: float
    width: float
    height: float


def build_figure():
    """Expose physical geometry and artists for automated layout checks."""
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42,
        'svg.fonttype': 'none', 'svg.hashsalt': 'science-utopia-lab-program-v2'})
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    fig.subplots_adjust(left=.012, right=.988, bottom=.012, top=.988)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    texts, routes, frames = [], [], {}

    def px(points):
        return points / (fig.get_figwidth() * 72 * .976)

    def py(points):
        return points / (fig.get_figheight() * 72 * .976)

    def text(x, y, value, size=8, color=None, weight='normal', ha='center', owner=None, **kw):
        artist = ax.text(x, y, value, fontsize=size, color=color or C['ink'],
            weight=weight, ha=ha, va='center', linespacing=1.18, zorder=6, **kw)
        texts.append((owner, artist))
        return artist

    def panel(name, bounds, fill, edge=None, rounding=.012):
        frame = Frame(*bounds)
        frames[name] = frame
        # Exact visible bounds: no boxstyle padding to offset arrow anchors.
        ax.add_patch(FancyBboxPatch((frame.x, frame.y), frame.width, frame.height,
            boxstyle=f'round,pad=0,rounding_size={rounding}', facecolor=fill,
            edgecolor=edge or C['line'], lw=.8, zorder=1))
        return frame

    def port(frame, side, along=.5, gap=4):
        return {'left': (frame.x-px(gap), frame.y+frame.height*along),
            'right': (frame.x+frame.width+px(gap), frame.y+frame.height*along),
            'top': (frame.x+frame.width*along, frame.y+frame.height+py(gap)),
            'bottom': (frame.x+frame.width*along, frame.y-py(gap))}[side]

    def route(points, color=None, head=6.5, lw=1.05, arrow=True, zorder=3):
        # One continuous shaft; no separately shortened final segment/seam.
        path = VectorPath(points, [VectorPath.MOVETO]+[VectorPath.LINETO]*(len(points)-1))
        artist = FancyArrowPatch(path=path, arrowstyle='-|>' if arrow else '-',
            mutation_scale=head, shrinkA=0, shrinkB=0, color=color or C['muted'],
            linewidth=lw, capstyle='round', joinstyle='round', zorder=zorder)
        ax.add_patch(artist)
        routes.append((path, artist))

    def disc(x, y, radius=3, fill='white', edge=None, lw=.8):
        ax.add_patch(Ellipse((x, y), 2*px(radius), 2*py(radius), facecolor=fill,
            edgecolor=edge or C['teal'], lw=lw, zorder=4))

    def dot_link(a, b, color=None, radius=3, arrow=True):
        delta = np.array([(b[0]-a[0])/px(1), (b[1]-a[1])/py(1)])
        unit = delta / np.linalg.norm(delta)
        offset = np.array([px(unit[0]*(radius+1.5)), py(unit[1]*(radius+1.5))])
        route([np.array(a)+offset, np.array(b)-offset], color, head=4.5, lw=.75, arrow=arrow)

    text(.025, .978, 'WHAT CAN CHANGE?', 8, C['teal'], 'bold', ha='left')
    text(.975, .978, 'Composable, not fixed stages', 7.2, C['muted'], ha='right')
    cards = []
    for i, (title, caption) in enumerate([
        ('Parameters', 'Tune values, keep the rule'),
        ('Algorithms / source', 'Rewrite executable rules'),
        ('Mechanisms', 'Create new institutions\nand message protocols'),
        ('Wiring / order', 'Rewire information flows\nChange execution order')]):
        x, name = .025+.242*i, f'freedom-{i}'
        cards.append(panel(name, (x, .768, .224, .18), '#F8FAFC'))
        text(x+.112, .921, title, 8, weight='bold', owner=name)
        text(x+.112, .801, caption, 6.45, C['muted'], owner=name)
    # Settings move while the rule/track remains in place.
    for y, old, new in [(.878, .085, .176), (.843, .186, .108)]:
        route([(.059, y), (.215, y)], C['line'], lw=1.2, arrow=False)
        disc(old, y, 3.1, 'white', C['muted'])
        disc(new, y, 3.1, C['teal'], C['teal'])
        shift = px(6) if new > old else -px(6)
        route([(old+shift, y), (new-shift, y)], C['teal'], head=4, lw=.8)
    # Executable function replacement, not just another numeric setting.
    for x, color, symbol in [(.294, C['muted'], '$f$'), (.413, C['teal'], '$g$')]:
        ax.add_patch(FancyBboxPatch((x, .835), .053, .062,
            boxstyle='round,pad=0,rounding_size=.004', facecolor='white', edgecolor=color, lw=.85, zorder=4))
        text(x+.0265, .867, symbol, 11, color, owner='freedom-1')
    route([(.361, .866), (.399, .866)], C['teal'], head=5, lw=.9)
    # A new mechanism and message edges, not a fixed institution catalog.
    left, right, new = (.548, .846), (.692, .846), (.620, .889)
    dot_link(left, right, C['line'], radius=3.5, arrow=False)
    dot_link(left, new, C['teal'], radius=3.5)
    dot_link(new, right, C['teal'], radius=3.5)
    disc(*left, 3.5, edge=C['muted'])
    disc(*right, 3.5, edge=C['muted'])
    disc(*new, 4.7, C['teal'], C['teal'])
    text(*new, '+', 9, 'white', owner='freedom-2')
    # Same colored nodes, different routes and implied execution order.
    before = [(.779, .884), (.823, .884), (.801, .838)]
    after = [(.905, .884), (.949, .884), (.927, .838)]
    for points, links in [(before, [(0, 1), (1, 2)]), (after, [(0, 2), (2, 1)])]:
        for a, b in links:
            dot_link(points[a], points[b], C['muted'], radius=2.6)
        for xy, color in zip(points, (C['blue'], C['teal'], C['purple'])):
            disc(*xy, 2.6, color, color)
    route([(.845, .863), (.882, .863)], C['teal'], head=5, lw=.9)
    # The four freedoms compose over one system, rather than form a pipeline.
    centers = [f.x+f.width/2 for f in cards]
    for frame, x in zip(cards, centers):
        route([port(frame, 'bottom', gap=3.5), (x, .748)], C['line'], arrow=False, lw=.75)
    route([(centers[0], .748), (centers[-1], .748)], C['line'], arrow=False, lw=.75)

    world = panel('world', (.300, .270, .400, .435), C['blue_bg'], '#B9CEE4')
    route([(.5, .748), port(world, 'top')], C['teal'], head=6)
    text(.5, .677, 'Scientific system $S$', 10, weight='bold', owner='world')
    text(.5, .643, 'Executable rules, mechanisms and flows', 7.15, C['teal'], owner='world')
    nodes = {}
    for key, x, y, label, color in [
        ('m1', .338, .563, '$M_1$', 'white'), ('m2', .468, .563, '$M_2$', 'white'),
        ('m3', .598, .563, '$M_3$', 'white'), ('new', .465, .510, '$M_{new}$', C['teal_bg'])]:
        nodes[key] = panel(key, (x, y, .064 if key != 'new' else .070, .044), color, '#77ADA2', rounding=.006)
        text(x+nodes[key].width/2, y+.022, label, 8, owner=key)
    for a, b in [('m1', 'm2'), ('m2', 'm3')]:
        route([port(nodes[a], 'right', gap=1.5), port(nodes[b], 'left', gap=1.5)], C['teal'], head=5, lw=.85)
    route([port(nodes['m1'], 'bottom', gap=1.5), (.37, .532), port(nodes['new'], 'left', gap=1.5)], C['teal'], head=5, lw=.85)
    route([port(nodes['new'], 'right', gap=1.5), (.63, .532), port(nodes['m3'], 'bottom', gap=1.5)], C['teal'], head=5, lw=.85)
    route([(.343, .507), (.343, .461)], C['teal'], head=5)
    route([(.657, .461), (.657, .507)], C['teal'], head=5)
    text(.5, .482, 'Institutions ↔ scientific activity', 7, C['muted'], owner='world')
    text(.5, .446, 'Responsive researcher agents', 7.7, weight='bold', owner='world')
    people = [(.348+.061*i, .393+.010*(i % 2)) for i in range(6)]
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 2), (3, 5)]:
        route([people[a], people[b]], '#B4C9DE', arrow=False, lw=.85)
    for i, (x, y) in enumerate(people):
        color = C['blue'] if i % 2 == 0 else '#6C91B7'
        disc(x, y+py(4), 3.2, color, color, lw=0)
        ax.add_patch(FancyBboxPatch((x-px(4.2), y-py(5)), px(8.4), py(7),
            boxstyle='round,pad=0,rounding_size=.004', facecolor=color, edgecolor='none', zorder=4))
    for x in (.418, .490, .562):
        ax.add_patch(Rectangle((x, .331), px(8), py(11), facecolor='white', edgecolor=C['muted'], lw=.6, zorder=4))
        for k in range(3):
            route([(x+px(1.5), .331+py(8-2*k)), (x+px(6.5), .331+py(8-2*k))], C['line'], arrow=False, lw=.65, zorder=5)
    text(.5, .296, 'Research • artifacts • exchange • resources', 6.9, C['muted'], owner='world')
    text(.5, .231, 'Contains the original researcher world;\nopen to richer scientific activity', 7.1, C['blue'])
    text(.125, .684, 'Choose the objective', 8.4, weight='bold')
    text(.125, .650, 'Explicit, replaceable loss', 7, C['muted'])
    for y, label, color, shift in [(.597, '$L_A$', C['blue'], -.008),
            (.541, '$L_B$', C['teal'], .018), (.485, '$L_C$', C['purple'], -.025)]:
        text(.042, y, label, 10, color)
        xs = np.linspace(.078, .210, 60)
        ax.plot(xs, y-.012+.022*np.minimum(((xs-(.139+shift))/.075)**2, 1.4), color=color, lw=1.25)
    text(.125, .424, 'Different losses may favor\ndifferent systems', 6.65, C['muted'])
    outcomes = panel('outcomes', (.7775, .455, .210, .179), '#F8FAFC')
    text(.8825, .602, 'Observe outcomes', 8, weight='bold', owner='outcomes')
    text(.8825, .540, 'Trajectories, outputs,\nparticipation, costs, …', 7, C['muted'], owner='outcomes')
    route([port(world, 'right', along=(.55-world.y)/world.height),
        port(outcomes, 'left', along=(.55-outcomes.y)/outcomes.height)], C['blue'])
    metrics = panel('metrics', (.7775, .250, .210, .126), '#F8FAFC')
    text(.8825, .345, 'Independent metrics', 7.25, weight='bold', owner='metrics')
    text(.8825, .294, 'Held-out seeds\nReport-only measures', 6.9, C['muted'], owner='metrics')
    route([port(outcomes, 'bottom'), port(metrics, 'top')])
    optimizer = panel('optimizer', (.300, .050, .400, .132), C['amber_bg'], '#E5CFAE')
    text(.5, .158, 'HOW TO SEARCH?', 7.5, C['amber'], 'bold', owner='optimizer')
    text(.5, .128, 'Black-box     Gradients     Hybrid', 8.6, weight='bold', owner='optimizer')
    text(.5, .102, 'Differentiable representations of the same world', 6.7, C['muted'], owner='optimizer')
    text(.5, .076, 'Whole-world backprop: research target', 6.7, C['muted'], owner='optimizer')
    route([(.125, .385), (.125, .128), port(optimizer, 'left', along=(.128-optimizer.y)/optimizer.height)], C['amber'])
    text(.141, .260, 'Declared\nloss $L$', 7.5, C['amber'], ha='left')
    route([port(outcomes, 'left', along=(.486-outcomes.y)/outcomes.height), (.737, .486),
        (.737, .128), port(optimizer, 'right', along=(.128-optimizer.y)/optimizer.height)], C['amber'])
    text(.756, .335, 'Evaluate $L(S)$', 7, C['amber'], rotation=90)
    route([port(optimizer, 'left', along=(.159-optimizer.y)/optimizer.height), (.255, .159),
        (.255, .605), port(world, 'left', along=(.605-world.y)/world.height)], C['amber'])
    text(.237, .386, 'Propose → execute → measure → revise', 7, C['amber'], rotation=90)
    text(.5, .016, 'Conceptual schematic - not empirical outcomes or a completion claim', 6.5, C['muted'])
    return fig, ax, {'texts': texts, 'routes': routes, 'frames': frames, 'port': port}


def make_figure(output=None):
    output = Path(output or ROOT / 'paper/figures/program-concept/science-system-design-program')
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, _, _ = build_figure()
    fig.savefig(output.with_suffix('.pdf'), metadata={'Title': 'Scientific systems as objects of design',
        'Subject': 'Composable design freedoms and optimization loop; conceptual, not completion evidence',
        'Creator': 'Science Utopia Lab', 'CreationDate': None, 'ModDate': None})
    fig.savefig(output.with_suffix('.png'), dpi=230)
    fig.savefig(output.with_suffix('.svg'), metadata={'Date': None})
    svg = output.with_suffix('.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)
    if output.parent == ROOT / 'paper/figures/program-concept':
        manifest = {'schema': 'scienceutopia.research-program-concept.v2',
            'classification': 'conceptual-not-empirical', 'generator': str(Path(__file__).relative_to(ROOT)),
            'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'caption': 'paper/research_program_concept.tex',
            'caption_sha256': hashlib.sha256((ROOT / 'paper/research_program_concept.tex').read_bytes()).hexdigest(),
            'design_freedoms': ['parameters', 'algorithms-source', 'mechanisms-protocols', 'wiring-order'],
            'standalone_game_ui_node': False, 'whole_world_backpropagation': 'research-target-not-established-result',
            'useful_autonomous_invention': 'research-target-not-established-result',
            'outputs': {output.with_suffix(s).name: hashlib.sha256(output.with_suffix(s).read_bytes()).hexdigest()
                for s in ('.pdf', '.png', '.svg')}}
        (output.parent / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    return output


if __name__ == '__main__':
    print(make_figure())
