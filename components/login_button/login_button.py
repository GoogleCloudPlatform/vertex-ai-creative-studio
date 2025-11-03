import mesop as me


@me.web_component(path="./login_button.js?v=2")
def login_button(*, label: str, password: str):
    return me.insert_web_component(
        name="login-button",
        properties={
            "label": label,
            "password": password,
        },
        events={},
    )


