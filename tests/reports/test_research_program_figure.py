import matplotlib.pyplot as plt
import hashlib
import json
from pathlib import Path as FilePath
from matplotlib.path import Path
from matplotlib.transforms import Bbox
import numpy as np

from scripts.figures.science_system_program import make_figure, build_figure


def test_program_concept_is_stable_vector_and_raster(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    make_figure(first)
    make_figure(second)
    for suffix in ('.pdf', '.svg', '.png'):
        assert first.with_suffix(suffix).read_bytes() == second.with_suffix(suffix).read_bytes()
    svg = first.with_suffix('.svg').read_text()
    for label in ('Composable, not fixed stages', 'Choose the objective',
            'Scientific system', 'Whole-world backprop: research target',
            'Independent metrics', 'Tune values, keep the rule',
            'Rewrite executable rules', 'Rewire information flows', 'Conceptual'):
        assert label in svg
    assert 'Game-like interface' not in svg


def test_concept_text_has_padding_no_overlap_and_no_canvas_clipping():
    fig, ax, layout = build_figure()
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        boxes = []
        for owner, artist in layout['texts']:
            bbox = artist.get_window_extent(renderer)
            assert fig.bbox.contains(bbox.x0, bbox.y0) and fig.bbox.contains(bbox.x1, bbox.y1), artist.get_text()
            boxes.append((artist.get_text(), bbox))
            if owner:
                f = layout['frames'][owner]
                limits = ax.transData.transform_bbox(Bbox.from_bounds(f.x, f.y, f.width, f.height))
                margins = np.array([bbox.x0-limits.x0, bbox.y0-limits.y0, limits.x1-bbox.x1, limits.y1-bbox.y1]) * 72/fig.dpi
                minimum = 2. if owner in {'m1', 'm2', 'm3', 'new'} else 4.
                assert min(margins) >= minimum, (owner, artist.get_text(), margins)
        for i, (label, box) in enumerate(boxes):
            for other, other_box in boxes[i+1:]:
                assert not box.overlaps(other_box), (label, other)
    finally:
        plt.close(fig)


def test_connector_shafts_are_single_continuous_paths_and_avoid_text():
    fig, ax, layout = build_figure()
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for path, artist in layout['routes']:
            assert path.codes[0] == Path.MOVETO
            assert all(code == Path.LINETO for code in path.codes[1:])
            assert artist.shrinkA == artist.shrinkB == 0
            assert np.linalg.norm(np.diff(path.vertices, axis=0), axis=1).min() > 0
            visible = ax.transData.transform_path(path)
            for _, label in layout['texts']:
                assert not visible.intersects_bbox(label.get_window_extent(renderer), filled=False), label.get_text()
    finally:
        plt.close(fig)


def test_tracked_concept_assets_caption_and_deliverable_match_manifest():
    root = FilePath(__file__).resolve().parents[2]
    directory = root / 'paper/figures/program-concept'
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['standalone_game_ui_node'] is False
    assert len(manifest['design_freedoms']) == 4
    for key in ('generator', 'caption'):
        assert hashlib.sha256((root / manifest[key]).read_bytes()).hexdigest() == manifest[key+'_sha256']
    for name, expected in manifest['outputs'].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    assert (root / 'output/pdf/science-utopia-lab-concept.pdf').read_bytes() == (directory / 'science-system-design-program.pdf').read_bytes()
