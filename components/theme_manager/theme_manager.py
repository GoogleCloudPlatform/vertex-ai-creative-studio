import mesop as me
import typing

@me.web_component(path="./theme_manager.js")
def theme_manager(
    *,
    theme: str,
    on_theme_load: typing.Callable[[me.WebEvent], None],
):
    return me.insert_web_component(
        name="theme-manager",
        properties={
            "theme": theme,
        },
        events={
            "themeLoaded": on_theme_load,
        },
    )
