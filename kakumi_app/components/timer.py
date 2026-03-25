"""
KAKUMI
Componente de temporizador
"""

import asyncio

import reflex as rx


class TimerState(rx.State):
    count: int = 90  # 01:30
    running: bool = False  # Bandera que indica si el tiempo está corriendo

    @rx.var
    def formatted_time(self) -> str:
        minutes = self.count // 60
        seconds = self.count % 60
        return f"{minutes:02d}:{seconds:02d}"

    @rx.event
    def toggle_running(self):
        self.running = not self.running
        if self.running:
            # Inicia la tarea de fondo directamente
            return TimerState.start_timer

    @rx.event(background=True)
    async def start_timer(self):
        # El bucle solo se ejecuta si running es True
        while True:
            await asyncio.sleep(1)
            async with self:
                # Si el usuario detuvo el timer o llegó a cero, sale del bucle
                if not self.running or self.count <= 0:
                    self.running = False
                    if self.count <= 0:
                        yield rx.toast.success(
                            "¡Combate terminado!", position="bottom-center"
                        )
                        self.count = 90
                    break
                self.count -= 1

    @rx.event
    def stop_timer(self):
        self.running = False

    @rx.event
    def reset_timer(self):
        self.running = False
        self.count = 90

    @rx.event
    def set_timer(self, seconds: int):  # Recibe los segundos como parámetro
        """Establece el tiempo en segundos."""
        if self.count == seconds:
            yield rx.toast.warning(
                f"Ya está establecido en {seconds // 60}:00 minutos."
            )
            return

        # Cambiar el tiempo
        self.count = seconds
        self.running = False

        # Mostrar mensaje
        minutes = seconds // 60
        yield rx.toast.info(f"Tiempo redefinido a {minutes:02d}:00 minutos.")

    @rx.event
    def add_or_substract_timer(self, seconds=int):
        """Suma o resta 1 o 10 segundos"""
        self.running = False
        match seconds:
            case seconds if seconds == 10:
                self.count += 10
            case seconds if seconds == 1:
                self.count += 1
            case seconds if seconds == -1:
                self.count -= 1
            case seconds if seconds == -10:
                self.count -= 10


def timer() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading(
                TimerState.formatted_time,
                size="9",
                font_family="Archivo Black",
            ),
            rx.hstack(
                rx.button(
                    rx.cond(~TimerState.running, "Comenzar", "Detener"),
                    on_click=TimerState.toggle_running,
                ),
                rx.button(
                    "Reiniciar", on_click=TimerState.reset_timer, color_scheme="blue"
                ),
                rx.button("Establecer 1 min", on_click=TimerState.set_timer(60)),
                rx.button("Establecer 3 min", on_click=TimerState.set_timer(180)),
            ),
            rx.hstack(
                rx.foreach(
                    {
                        "+10 Segundos": 10,
                        "+1 Segundo": 1,
                        "-1 Segundo": -1,
                        "-10 Segundos": -10,
                    },
                    lambda i: rx.button(
                        i[0], on_click=TimerState.add_or_substract_timer(i[1])
                    ),
                ),
            ),
        )
    )
