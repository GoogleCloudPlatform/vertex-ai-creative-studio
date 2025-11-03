
import mesop as me
from components.svg_icon.svg_icon import svg_icon

@me.page(path="/test_svg")
def test_svg_page():
    with me.box(style=me.Style(width=100, height=100)):
        me.icon(icon="info")
