import json
import mesop as me
import typing

from common.metadata import MediaItem


def get_pills_for_item(item: MediaItem, https_url: str) -> str:
    """Generates a JSON string of pill data for a given media item."""
    pills = []
    # Infer type if missing, to make pill generation more robust.
    effective_media_type = item.media_type
    if not effective_media_type and https_url:
        if ".wav" in https_url or ".mp3" in https_url:
            effective_media_type = "audio"
        elif ".mp4" in https_url or ".webm" in https_url:
            effective_media_type = "video"
        else:
            effective_media_type = "image"

    if effective_media_type == "video":
        pills.append({"label": "Video"})
        if item.gcs_uris and len(item.gcs_uris) > 1:
            pills.append({"label": f"{len(item.gcs_uris)}"})
        if item.r2v_reference_images or item.r2v_style_image:
            pills.append({"label": "r2v"})
        elif item.mode:
            pills.append({"label": item.mode})
        else:
            pills.append({"label": "t2v" if not item.reference_image else "i2v"})
        if item.aspect:
            pills.append({"label": item.aspect})
        if item.duration is not None:
            pills.append({"label": f"{item.duration} sec"})
    elif effective_media_type == "image":
        pills.append({"label": "Image"})
        if item.aspect:
            pills.append({"label": item.aspect})
        if len(item.gcs_uris) > 1:
            pills.append({"label": str(len(item.gcs_uris))})
    elif effective_media_type == "audio":
        pills.append({"label": "Audio"})
        if item.duration is not None:
            pills.append({"label": f"{item.duration} sec"})
    elif effective_media_type == "interior_design_tour":
        pills.append({"label": "Interior Design"})

    return json.dumps(pills)


@me.web_component(path="./media_tile.js")
def media_tile(
    *,
    media_type: str | None,
    https_url: str,
    pills_json: str,
    on_click: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the media_tile web component."""
    effective_media_type = media_type
    if not effective_media_type and https_url:
        if ".wav" in https_url or ".mp3" in https_url:
            effective_media_type = "audio"
        elif ".mp4" in https_url or ".webm" in https_url:
            effective_media_type = "video"
        else:
            effective_media_type = "image"

    return me.insert_web_component(
        key=key,
        name="media-tile",
        properties={
            "mediaType": effective_media_type or "",
            "thumbnailSrc": https_url if effective_media_type != "audio" else "",
            "audioSrc": https_url if effective_media_type == "audio" else "",
            "pillsJson": pills_json,
        },
        events={
            "clickEvent": on_click,
        },
    )
