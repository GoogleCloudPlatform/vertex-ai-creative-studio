import mesop as me
import typing

@me.web_component(path="/components/drawing/image_drawer.js")
def image_drawer(
    *,
    image_url: str,
    pen_color: str,
    pen_width: int,
    on_save: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the image drawing web component."""
    return me.insert_web_component(
        key=key,
        name="image-drawer",
        properties={
            "imageUrl": image_url,
            "penColor": pen_color,
            "penWidth": pen_width,
        },
        events={
            "save": on_save,
        },
    )
