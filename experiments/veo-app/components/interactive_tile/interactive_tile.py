import mesop as me
import typing

@me.web_component(path="./interactive_tile.js")
def interactive_tile(
    *,
    label: str,
    icon: str,
    description: str,
    route: str,
    video_url: str = "",
    video_object_position: str = "center",
    default_bg_color: str = "",
    default_text_color: str = "",
    hover_bg_color: str = "",
    hover_text_color: str = "",
    on_tile_click: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the interactive tile web component."""
    return me.insert_web_component(
        key=key,
        name="interactive-tile",
        properties={
            "label": label,
            "icon": icon,
            "description": description,
            "route": route,
            "videoUrl": video_url,
            "videoObjectPosition": video_object_position,
            "defaultBgColor": default_bg_color,
            "defaultTextColor": default_text_color,
            "hoverBgColor": hover_bg_color,
            "hoverTextColor": hover_text_color,
        },
        events={
            "tileClickEvent": on_tile_click,
        },
    )
