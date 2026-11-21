"""Extract inline browser scripts for Node syntax validation (no execution)."""
from html.parser import HTMLParser
from pathlib import Path

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.parts = []
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.capture = 'src' not in dict(attrs)
            self.parts = []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.capture:
            self.count += 1
            Path(f'/tmp/festival-radar-script-{self.count}.mjs').write_text(''.join(self.parts))
            self.capture = False

if __name__ == '__main__':
    parser = Scripts()
    parser.feed(Path('index.html').read_text())
    assert parser.count >= 3
    print(f'Extracted {parser.count} inline scripts for syntax validation')
