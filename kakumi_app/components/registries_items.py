import reflex as rx

from kakumi_app.styles.tokens import (
    BRAND_RED_HOVER,
    BRAND_RED_HOVER_LIGHT,
    TEXT_WHITE,
)

ICON_SIZE = "75px"
CARD_SIZE = "40vh"
CARD_PADDING = "5rem"
CARD_RADIUS = "0.5em"
ICON_STYLE = {"filter": "invert(1)", "color": TEXT_WHITE}
CARD_STYLE = {
    "cursor": "pointer",
    "bg": BRAND_RED_HOVER,
    "border_radius": CARD_RADIUS,
    "_hover": {
        "bg": BRAND_RED_HOVER_LIGHT,
        "color": TEXT_WHITE,
        "transition": "0.5s ease",
    },
}


def _registry_icon(icon_path: str) -> rx.Component:
    """Render registry icon image with shared sizing and filter."""
    return rx.image(
        icon_path,
        style=ICON_STYLE,
        width=ICON_SIZE,
        height=ICON_SIZE,
    )


def _registry_card_body(text: str, icon_component: rx.Component) -> rx.Component:
    """Render shared registry card content."""
    return rx.vstack(
        icon_component,
        rx.text(text, font_size="20px", color=TEXT_WHITE, font_weight="bold"),
        width="100%",
        height="100%",
        align="center",
        justify="center",
        padding=CARD_PADDING,
        style=CARD_STYLE,
    )


def reg_item(text: str, icon: str | rx.Component, href: str) -> rx.Component:
    """Single registry card accepting icon path or component."""
    if isinstance(icon, str):
        icon_component = _registry_icon(icon)

    else:
        icon_component = icon

    return rx.link(
        _registry_card_body(text, icon_component),
        href=href,
        underline="none",
        weight="medium",
        width=CARD_SIZE,
        height=CARD_SIZE,
    )


def reg_items() -> rx.Component:
    """Registry launcher grid."""
    return rx.hstack(
        reg_item("Atletas", "icons/cinturon.png", "/registries/athletes"),
        reg_item("Torneos", "icons/categoria.png", "/registries/tournaments"),
        reg_item("Árbitros", "icons/silbato.png", "/registries/referees"),
        spacing="5",
        width="100%",
        justify="center",
    )
