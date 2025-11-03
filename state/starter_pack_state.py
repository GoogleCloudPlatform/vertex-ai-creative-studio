import mesop as me

@me.stateclass
class StarterPackState:
  selected_tab_index: int = 0
  # Input images
  look_image_uri: str = ""
  starter_pack_image_uri: str = ""
  model_image_uri: str = ""

  # Output images
  generated_starter_pack_uri: str = ""
  generated_look_uri: str = ""

  # Virtual model generation inputs (similar to VTO)
  virtual_model_prompt: str = ""

  # Loading indicators
  is_generating_starter_pack: bool = False
  is_generating_look: bool = False
  is_generating_virtual_model: bool = False
