"""
Users Admin Page
RBAC-managed user administration (OPERATOR+ only).
"""

import reflex as rx
from kakumi_app.states.auth_state import AuthState
from kakumi_app.states.user_admin_state import UserAdminState
from kakumi_app.components.sidebar import sidebar


def users_table() -> rx.Component:
    """Table displaying system users."""
    state = UserAdminState

    return rx.vstack(
        # Search + Create bar
        rx.hstack(
            rx.input(
                placeholder="Buscar usuarios...",
                on_change=state.set_search_query,
                width="300px",
            ),
            rx.button(
                "Buscar",
                on_click=state.filter_users,
                color_scheme="blue",
            ),
            rx.button(
                "+ Nuevo Usuario",
                on_click=state.open_create_form,
                color_scheme="green",
            ),
            spacing="4",
            margin_bottom="1em",
        ),
        # Error message
        rx.cond(
            state.error_message,
            rx.callout(
                state.error_message,
                icon="circle_alert",
                color_scheme="red",
                margin_bottom="1em",
            ),
        ),
        # Users table
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Usuario"),
                    rx.table.column_header_cell("Email"),
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Rol"),
                    rx.table.column_header_cell("Activo"),
                    rx.table.column_header_cell("Acciones"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state.users,
                    lambda user: rx.table.row(
                        rx.table.cell(user["username"]),
                        rx.table.cell(user["email"]),
                        rx.table.cell(
                            rx.cond(user["full_name"], user["full_name"], "-"),
                        ),
                        rx.table.cell(
                            rx.select(
                                ["ADMIN", "OPERATOR", "VIEWER"],
                                value=user["role"],
                                on_change=lambda role, uid=user["id"]: (
                                    state.update_user_role(uid, role)
                                ),
                                size="2",
                            ),
                        ),
                        rx.table.cell(
                            rx.cond(
                                user["is_active"],
                                rx.badge("Sí", color_scheme="green"),
                                rx.badge("No", color_scheme="red"),
                            ),
                        ),
                        rx.table.cell(
                            rx.hstack(
                                rx.button(
                                    rx.cond(user["is_active"], "Desactivar", "Activar"),
                                    on_click=lambda: state.toggle_user_active(
                                        user["id"]
                                    ),
                                    color_scheme=rx.cond(
                                        user["is_active"], "orange", "green"
                                    ),
                                    size="2",
                                ),
                                rx.button(
                                    "Editar",
                                    on_click=lambda: state.open_edit_form(user),
                                    color_scheme="blue",
                                    size="2",
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=lambda: state.confirm_delete(
                                        user["id"], user["username"]
                                    ),
                                    color_scheme="red",
                                    size="2",
                                ),
                                spacing="2",
                            ),
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        # Delete confirmation dialog
        rx.cond(
            state.show_delete_confirm,
            rx.box(
                rx.vstack(
                    rx.heading("Confirmar eliminación", font_size="xl"),
                    rx.text(
                        f"¿Estás seguro de eliminar al usuario '{UserAdminState.deleting_username}'?",
                    ),
                    rx.text(
                        "Esta acción no se puede deshacer.",
                        font_size="sm",
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancelar",
                            on_click=UserAdminState.cancel_delete,
                            color_scheme="gray",
                        ),
                        rx.button(
                            "Eliminar",
                            on_click=UserAdminState.delete_user,
                            color_scheme="red",
                        ),
                        spacing="4",
                        margin_top="1em",
                    ),
                    spacing="4",
                    padding="2em",
                ),
                position="fixed",
                top="0",
                left="0",
                width="100vw",
                height="100vh",
                bg="rgba(0,0,0,0.5)",
                z_index="1000",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
        ),
        width="100%",
    )


def user_form() -> rx.Component:
    """Form for creating/editing a system user."""
    state = UserAdminState

    return rx.box(
        rx.vstack(
            rx.heading(
                rx.cond(state.is_editing, "Editar Usuario", "Crear Usuario"),
                font_size="2xl",
                margin_bottom="1em",
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="Nombre de usuario *",
                        value=state.form_username,
                        on_change=state.set_form_username,
                        width="100%",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Email *",
                        type="email",
                        value=state.form_email,
                        on_change=state.set_form_email,
                        width="100%",
                        required=True,
                    ),
                    rx.input(
                        placeholder=rx.cond(
                            state.is_editing,
                            "Contraseña (dejar vacío para mantener)",
                            "Contraseña *",
                        ),
                        type="password",
                        value=state.form_password,
                        on_change=state.set_form_password,
                        width="100%",
                        required=~state.is_editing,
                    ),
                    rx.input(
                        placeholder="Nombre completo *",
                        value=state.form_full_name,
                        on_change=state.set_form_full_name,
                        width="100%",
                        required=True,
                    ),
                    rx.select(
                        ["ADMIN", "OPERATOR", "VIEWER"],
                        value=state.form_role,
                        on_change=state.set_form_role,
                        width="100%",
                        placeholder="Seleccionar rol",
                    ),
                    rx.checkbox(
                        "Activo",
                        checked=state.form_is_active,
                        on_change=state.set_form_is_active,
                    ),
                    rx.hstack(
                        rx.button(
                            "Guardar",
                            type="submit",
                            color_scheme="green",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=state.cancel_form,
                            color_scheme="gray",
                        ),
                        spacing="4",
                        margin_top="1em",
                    ),
                    spacing="4",
                ),
                on_submit=state.save_user,
            ),
        ),
        padding="2em",
        border="1px solid #ddd",
        border_radius="8px",
        margin_bottom="2em",
    )


def users_page() -> rx.Component:
    """Main users admin page."""
    state = UserAdminState

    return rx.cond(
        AuthState.is_operator,
        # Has permission
        rx.box(
            rx.vstack(
                rx.hstack(
                    sidebar(),
                    rx.vstack(
                        rx.heading(
                            "Gestión de Usuarios",
                            font_size="3xl",
                            font_weight="bold",
                            margin_bottom="0.5em",
                        ),
                        rx.text(
                            "Administrar usuarios del sistema",
                            font_size="md",
                            margin_bottom="1em",
                        ),
                        rx.cond(
                            state.show_form,
                            user_form(),
                            users_table(),
                        ),
                        width="100%",
                        padding="2em",
                    ),
                    width="100%",
                ),
                width="100%",
                min_height="100vh",
            ),
            width="100%",
        ),
        # Denied
        rx.box(
            rx.vstack(
                rx.heading(
                    "Access Denied",
                    font_size="3xl",
                    font_weight="bold",
                    color="red",
                ),
                rx.text(
                    "You don't have permission to access this page.",
                    font_size="lg",
                ),
                rx.button(
                    "Go Home",
                    on_click=rx.redirect("/"),
                    color_scheme="blue",
                    margin_top="1em",
                ),
                spacing="4",
                justify_content="center",
                align_items="center",
                min_height="50vh",
            ),
            width="100%",
            padding="2em",
            on_mount=rx.toast.error("Access denied"),
        ),
    )


@rx.page(route="/admin/users", title="Kakumi | Usuarios")
def users() -> rx.Component:
    """Route for users management page."""
    return users_page()
