"""The layout scanner must count every Poppler word, not only regex matches."""
import pytest

from scripts.reports.integrated_native_numeric_build_v1 import Bounds


def test_all_case_normalized_word_attributes_are_counted():
    scan = Bounds()
    scan.feed('<page width="612" height="792"><word xMin="1" yMin="2" '
              'xMax="30" yMax="20">inside</word><word xMin="600" yMin="2" '
              'xMax="613" yMax="20">outside</word></page>')
    assert (scan.pages, scan.words, scan.outside, scan.size) == (1, 2, 1, None)


@pytest.mark.parametrize('coords', ['-1,2,3,4', '3,2,1,4', '1,5,3,4', '1,2,3,793'])
def test_invalid_bounds_are_not_silently_skipped(coords):
    x0, y0, x1, y1 = coords.split(',')
    scan = Bounds()
    scan.feed(f'<page width="612" height="792"><word xmin="{x0}" ymin="{y0}" '
              f'xmax="{x1}" ymax="{y1}">bad</word></page>')
    assert scan.words == scan.outside == 1


def test_word_after_page_is_rejected():
    scan = Bounds()
    scan.feed('<page width="612" height="792"></page>')
    with pytest.raises(ValueError, match='outside'):
        scan.feed('<word xmin="1" ymin="2" xmax="3" ymax="4">bad</word>')
