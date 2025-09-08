import mesop as me
import typing

@me.web_component(path="./welcome_hero.js")
def welcome_hero(
    *,
    title: str,
    subtitle: str,
    video_url: str,
    tiles: str, # JSON string
    on_tile_click: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the welcome hero web component."""
    return me.insert_web_component(
        key=key,
        name="welcome-hero",
        properties={
            "title": title,
            "subtitle": subtitle,
            "videoUrl": video_url,
            "tiles": tiles,
        },
        events={
            "tileClickEvent": on_tile_click,
        },
    )
