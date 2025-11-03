import mesop as me
import typing

@me.web_component(path="./video_thumbnail.js")
def video_thumbnail(
    *,
    video_src: str,
    selected: bool = False,
    on_click: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """A clickable video thumbnail with mouse-over autoplay and selection state."""
    return me.insert_web_component(
        key=key,
        name="video-thumbnail",
        properties={
            "videoSrc": video_src,
            "selected": selected,
        },
        events={
            "thumbnailClick": on_click,
        },
    )