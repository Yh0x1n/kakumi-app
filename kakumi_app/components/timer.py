import reflex as rx

from kakumi_app.states.kumite_match_state import KumiteMatchState


def timer() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading(
                KumiteMatchState.timer_formatted,
                size="9",
            ),
            rx.hstack(
                rx.button(
                    rx.cond(~KumiteMatchState.timer_running, "Comenzar", "Detener"),
                    on_click=rx.cond(
                        ~KumiteMatchState.timer_running,
                        KumiteMatchState.start_timer,
                        KumiteMatchState.stop_timer,
                    ),
                ),
                rx.button(
                    "Reiniciar",
                    on_click=KumiteMatchState.reset_timer,
                    color_scheme="blue",
                ),
            ),
            rx.hstack(
                rx.button("Establecer 1 min", on_click=KumiteMatchState.set_timer(60)),
                rx.button(
                    "Establecer 3 min",
                    on_click=KumiteMatchState.set_timer(180),
                ),
                wrap="wrap",
                justify="center",
                width="100%",
            ),
            rx.hstack(
                rx.foreach(
                    {
                        "+10": 10,
                        "+1": 1,
                        "-1": -1,
                        "-10": -10,
                    },
                    lambda i: rx.button(
                        i[0],
                        on_click=KumiteMatchState.add_or_substract_timer(i[1]),
                    ),
                ),
                justify="center",
                width="100%",
            ),
            align="center",
            width="100%",
        )
    )
