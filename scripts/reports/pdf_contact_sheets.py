"""Make labelled review sheets from already rendered PDF pages (no PDF edits)."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--pattern', default='page-*.png')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pages = sorted(args.directory.glob(args.pattern))
    if not pages:
        parser.error('render PDF pages first')
    args.output.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(pages), 12):
        sheet = Image.new('RGB', (1800, 4 * 800), '#dadde1')
        draw = ImageDraw.Draw(sheet)
        for index, path in enumerate(pages[start:start + 12]):
            with Image.open(path) as page:
                page = page.convert('RGB')
                page.thumbnail((580, 755))
                x, y = (index % 3) * 600 + 10, (index // 3) * 800 + 30
                sheet.paste(page, (x, y))
                draw.text((x, y - 20), path.name, fill='black')
        sheet.save(args.output / f'sheet-{start // 12 + 1:02d}.png')
    print(f'{len(pages)} pages in {(len(pages) + 11) // 12} review sheets')


if __name__ == '__main__':
    main()
