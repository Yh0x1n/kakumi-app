"""Kakumi Sidebar Component Module."""

# Imports
import reflex as rx


def sidebar_item(text: str, icon: str, href: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(icon, color="white"),
            rx.text(text, size="5", color="#ffffff"),
            width="100%",
            align="center",
            padding_x="0.5rem",
            padding_y="0.75rem",
            style={
                "_hover": {
                    "bg": "#612727",
                    "color": "#ffffff",
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


def sidebar_items() -> rx.Component:
    return rx.vstack(
        sidebar_item("Torneo", "trophy", "/tournament"),
        sidebar_item("Exhibición", "eye", "/exhibition"),
        sidebar_item("Registros", "square-library", "/registries"),
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
                    color="black",
                    style={
                        "_hover": {
                            "background-color": "#e0e0e0",
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
                        rx.box(
                            rx.vstack(
                                # Encabezado
                                rx.hstack(
                                    # Botón que cierra la sidebar
                                    rx.drawer.close(
                                        rx.icon("x", size=30, color="white"),
                                        style={
                                            "_hover": {
                                                "bg": "#612727",
                                                "cursor": "pointer",
                                                "border-radius": "0.5em",
                                                "transition": "0.5s ease",
                                            },
                                        },
                                    ),
                                    rx.image(
                                        src="/icons/karategi.ico", height="1.5em"
                                    ),
                                    rx.link(
                                        rx.heading(
                                            "Kakumi",
                                            font_size=24,
                                            color="white",
                                            font_weight="bold",
                                            style={
                                                "_hover": {
                                                    "cursor": "pointer",
                                                    "color": "#dfc52eb0",
                                                    "transition": "0.5s ease",
                                                }
                                            },
                                        ),
                                        href="/",
                                        underline="none",
                                    ),
                                ),
                                rx.divider(
                                    border_color="#dfc52eb0", border_width="0.5px"
                                ),  # Separador
                                # Objetos de la sidebar
                                sidebar_items(),
                                # Estilo del contenedor de los objetos
                                bg=rx.color("crimson", 2),
                                align="start",
                                padding_x="1em",
                                padding_y="1.5em",
                                width="17.5em",
                                height="100vh",
                            ),
                            # Estilo del contenedor de la sidebar
                            style={
                                "background-color": "#c53030",
                                "height": "100%",
                                "position": "fixed",
                                "top": "0",
                                "left": "0",
                            },
                            width="100%",
                        ),
                    ),
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
