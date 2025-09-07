import mesop as me

@me.web_component(path="./svg_icon.js")
def svg_icon(
    *,
    icon_name: str,
    key: str | None = None,
):
    """Defines the API for the svg_icon web component."""
    return me.insert_web_component(
        key=key,
        name="svg-icon",
        properties={
            "iconName": icon_name,
        },
    )
