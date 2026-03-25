import reflex as rx


def reg_item(text: str, icon: str, href: str) -> rx.Component:
    if isinstance(icon, str):
        icon_component = rx.image(
            icon,
            style={"filter": "invert(1)", "color": "white"},
            width="75px",
            height="75px",
        )

    else:
        icon_component = icon

    return rx.link(
        rx.vstack(
            icon_component,
            rx.text(text, font_size="20px", color="#ffffff", font_weight="bold"),
            width="100%",
            height="100%",
            align="center",
            justify="center",
            padding="5rem",
            style={
                "cursor": "pointer",
                "bg": "#612727",
                "border_radius": "0.5em",
                "_hover": {
                    "bg": "#7a3838",
                    "color": "#ffffff",
                    "transition": "0.5s ease",
                },
            },
        ),
        href=href,
        underline="none",
        weight="medium",
        width="40vh",
        height="40vh",
    )


def reg_items() -> rx.Component:
    return rx.hstack(
        reg_item("Atletas", "icons/cinturon.png", "/registries/athletes"),
        reg_item("Categorías", "icons/categoria.png", "/registries/categories"),
        reg_item("Árbitros", "icons/silbato.png", "/registries/referees"),
        spacing="5",
        width="100%",
        justify="center",
    )
