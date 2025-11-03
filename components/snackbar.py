import mesop as me
from typing import Callable

@me.component
def snackbar(
  *,
  is_visible: bool,
  label: str,
):
  """Creates a simple snackbar."""
  with me.box(
    style=me.Style(
      display="block" if is_visible else "none",
      position="fixed",
      bottom=20,
      left="50%",
      transform="translateX(-50%)",
      z_index=1000,
    )
  ):
    with me.box(
      style=me.Style(
        background=me.theme_var("on-surface-variant"),
        color=me.theme_var("surface-container-lowest"),
        padding=me.Padding.symmetric(vertical=10, horizontal=20),
        border_radius=8,
        box_shadow="0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f",
      )
    ):
      me.text(label)
