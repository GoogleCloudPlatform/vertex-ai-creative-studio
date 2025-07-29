import mesop as me

from components.drawing.image_drawer import image_drawer
from components.header import header
from components.library.infinite_scroll_chooser_button import (
    infinite_scroll_chooser_button,
)
from components.page_scaffold import page_frame, page_scaffold
from state.state import AppState


@me.stateclass
class PageState:
    """Local page state."""

    selected_gcs_uri: str = ""
    pen_color: str = "#ff0000"
    pen_width: int = 4


@me.page(path="/doodle")
def doodle_page():
    """Doodle page."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    with page_scaffold():  # pylint: disable = E1129:not-context-manager
        with page_frame():  # pylint: disable = E1129:not-context-manager
            header("Doodle Pad", "edit")

            with me.box(
                style=me.Style(
                    padding=me.Padding.all(24),
                    display="flex",
                    flex_direction="column",
                    gap=16,
                ),
            ):
                me.text("Select an image to start doodling", type="headline-5")

                infinite_scroll_chooser_button(
                    on_library_select=lambda e: on_image_select(e.gcs_uri),
                    button_label="Choose from Library",
                )

                if state.selected_gcs_uri:
                    image_drawer(
                        image_url=state.selected_gcs_uri,
                        pen_color=state.pen_color,
                        pen_width=state.pen_width,
                    )


def on_image_select(gcs_uri: str):
    state = me.state(PageState)
    state.selected_gcs_uri = gcs_uri
    yield
