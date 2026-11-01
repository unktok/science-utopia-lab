from scripts.figures.science_system_program import make_figure


def test_program_concept_is_stable_vector_and_raster(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    make_figure(first)
    make_figure(second)
    for suffix in ('.pdf', '.svg', '.png'):
        assert first.with_suffix(suffix).read_bytes() == second.with_suffix(suffix).read_bytes()
    svg = first.with_suffix('.svg').read_text()
    for label in ('Composable design freedoms', 'Choose the objective',
            'Design the scientific system', 'Whole-world backprop: research target',
            'Independent evaluation', 'Game-like interface', 'Conceptual'):
        assert label in svg
