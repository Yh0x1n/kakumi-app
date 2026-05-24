"""Kakumi Sidebar Component Module."""

# Imports
import reflex as rx
from kakumi_app.states.auth_state import AuthState
from kakumi_app.styles.tokens import (
    ACCENT_GOLD,
    BRAND_RED,
    BRAND_RED_HOVER,
    HOVER_GRAY,
    TEXT_PRIMARY,
    TEXT_WHITE,
)


def sidebar_item(text: str, icon: str, href: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(icon, color="white"),
            rx.text(text, size="5", color=TEXT_WHITE),
            width="100%",
            align="center",
            padding_x="0.5rem",
            padding_y="0.75rem",
            style={
                "_hover": {
                    "bg": BRAND_RED_HOVER,
                    "color": TEXT_WHITE,
                    "border-radius": "0.5em",
                    "transition": "0.5s ease",
                },
            },
        ),
        href=href,
        underline="none",
        weight="medium",
        width="100%",
    )


def sidebar_logout() -> rx.Component:
    """Logout button styled like a sidebar item."""
    return rx.button(
        rx.hstack(
            rx.icon("log-out", color="white"),
            rx.text("Cerrar sesión", size="5", color=TEXT_WHITE),
            width="100%",
            align="center",
            padding_x="0.5rem",
            padding_y="0.75rem",
        ),
        on_click=AuthState.logout,
        variant="ghost",
        width="100%",
        style={
            "_hover": {
                "bg": BRAND_RED_HOVER,
                "color": TEXT_WHITE,
                "border-radius": "0.5em",
                "transition": "0.5s ease",
            },
            "cursor": "pointer",
        },
    )


def sidebar_items() -> rx.Component:
    return rx.vstack(
        sidebar_item("Torneo", "trophy", "/tournament"),
        sidebar_item("Exhibición", "eye", "/exhibition"),
        sidebar_item("Resultados", "medal", "/results"),
        sidebar_item("Registros", "square-library", "/registries"),
        rx.cond(
            AuthState.is_operator,
            rx.vstack(
                rx.divider(),
                sidebar_item("Equipos", "users", "/admin/teams"),
                sidebar_item("Atletas", "user", "/admin/athletes"),
                sidebar_item("Árbitros", "gavel", "/admin/referees"),
                sidebar_item("Exportar", "download", "/admin/export"),
                sidebar_item("Importar", "upload", "/admin/import"),
                sidebar_item("Usuarios", "shield", "/admin/users"),
                spacing="3",
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.drawer.root(
            rx.drawer.trigger(
                # Botón que abre la sidebar
                rx.icon(
                    "align-justify",
                    size=35,
                    color=TEXT_PRIMARY,
                    style={
                        "_hover": {
                            "background-color": HOVER_GRAY,
                            "transition": "0.5s ease",
                        },
                        "border-radius": "0.5em",
                    },
                    padding="3px",
                ),
            ),
            rx.drawer.overlay(z_index="5"),
            rx.drawer.portal(
                rx.drawer.content(
                    rx.vstack(
                        # Fixed header (always visible)
                        rx.vstack(
                            rx.hstack(
                                # Botón que cierra la sidebar
                                rx.drawer.close(
                                    rx.icon("x", size=30, color="white"),
                                    style={
                                        "_hover": {
                                            "bg": BRAND_RED_HOVER,
                                            "cursor": "pointer",
                                            "border-radius": "0.5em",
                                            "transition": "0.5s ease",
                                        },
                                    },
                                ),
                                rx.image(src="/icons/karategi.ico", height="1.5em"),
                                rx.link(
                                    rx.heading(
                                        "Kakumi",
                                        font_size=24,
                                        color="white",
                                        font_weight="bold",
                                        style={
                                            "_hover": {
                                                "cursor": "pointer",
                                                "color": ACCENT_GOLD,
                                                "transition": "0.5s ease",
                                            }
                                        },
                                    ),
                                    href="/",
                                    underline="none",
                                ),
                            ),
                            rx.divider(border_color=ACCENT_GOLD, border_width="0.5px"),
                            width="100%",
                            spacing="0",
                        ),
                        # Scrollable area (items + spacer + logout)
                        rx.vstack(
                            sidebar_items(),
                            rx.spacer(),
                            rx.divider(),
                            sidebar_logout(),
                            width="100%",
                            flex="1",
                            overflow_y="auto",
                        ),
                        # Estilo del contenedor de la sidebar
                        bg=rx.color("crimson", 2),
                        align="start",
                        padding_x="1em",
                        padding_y="1.5em",
                        width="17.5em",
                        max_height="100vh",
                    ),
                    style={
                        "background-color": BRAND_RED,
                    },
                    top="auto",
                    right="auto",
                    height="100%",
                    width="20em",
                    padding="1em",
                    bg=rx.color("crimson", 2),
                ),
                width="100%",
            ),
            direction="left",
        ),
        padding="1em",
    )
