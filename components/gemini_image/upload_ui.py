import mesop as me
from components.image_thumbnail import image_thumbnail
from components.library.library_chooser_button import library_chooser_button

@me.component
def gemini_image_upload_ui(
    state,
    model_config,
    on_upload,
    on_media_select,
    on_remove_image,
):
    """Shared upload UI with flex-wrap slots and library picker."""
    max_input_images = model_config.max_input_images if model_config else 3
    upload_disabled = len(state.uploaded_image_gcs_uris) >= max_input_images

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=16,
            margin=me.Margin(bottom=16),
            justify_content="center",
        ),
    ):
        me.uploader(
            label="Upload Media",
            on_upload=on_upload,
            multiple=True,
            accepted_file_types=["image/jpeg", "image/png", "image/webp", "application/pdf"],
            style=me.Style(width="100%"),
            disabled=upload_disabled,
        )
        library_chooser_button(
            on_library_select=on_media_select,
            button_label="Choose from Library",
            disabled=upload_disabled,
        )
        
    if state.uploaded_image_gcs_uris:
        with me.box(
            style=me.Style(
                display="flex",
                flex_wrap="wrap",
                gap=10,
                justify_content="center",
                margin=me.Margin(bottom=16),
            ),
        ):
            for i, uri in enumerate(state.uploaded_image_display_urls):
                image_thumbnail(
                    image_uri=uri,
                    index=i,
                    on_remove=on_remove_image,
                    icon_size=18,
                )
