"""Read-only public state for secondary scoring display route."""

from __future__ import annotations

import asyncio
from typing import Any

import reflex as rx

from kakumi_app.services.secondary_display_service import SecondaryDisplayService


class SecondaryDisplayState(rx.State):
    """State that loads and polls public display snapshots by display key."""

    current_display_key: str = ""
    modality: str = ""
    source_kind: str = ""
    snapshot: dict[str, Any] = {}
    has_snapshot: bool = False
    is_stale: bool = False
    is_loading: bool = False
    error_message: str = ""

    stale_after_seconds: int = 8

    @rx.var
    def kata_title(self) -> str:
        return str(self.snapshot.get("title") or "Kata en vivo")

    @rx.var
    def kata_aka_name(self) -> str:
        aka = self.snapshot.get("aka", {})
        return str(aka.get("name") or "ATLETA 1") if isinstance(aka, dict) else "ATLETA 1"

    @rx.var
    def kata_ao_name(self) -> str:
        ao = self.snapshot.get("ao", {})
        return str(ao.get("name") or "ATLETA 2") if isinstance(ao, dict) else "ATLETA 2"

    @rx.var
    def kata_aka_total(self) -> str:
        if self.kata_majority_tally_visible:
            votes = self.snapshot.get("majority_aka_votes")
            if isinstance(votes, int):
                return str(votes)
        aka = self.snapshot.get("aka", {})
        return str(aka.get("total") or "—") if isinstance(aka, dict) else "—"

    @rx.var
    def kata_ao_total(self) -> str:
        if self.kata_majority_tally_visible:
            votes = self.snapshot.get("majority_ao_votes")
            if isinstance(votes, int):
                return str(votes)
        ao = self.snapshot.get("ao", {})
        return str(ao.get("total") or "—") if isinstance(ao, dict) else "—"

    @rx.var
    def kata_judge_detail_visible(self) -> bool:
        return bool(self.snapshot.get("judge_detail_visible", False))

    @rx.var
    def kata_judge_detail_lines(self) -> list[str]:
        raw = self.snapshot.get("judge_detail_lines", [])
        if not isinstance(raw, list):
            return []
        return [str(item) for item in raw]

    @rx.var
    def kata_majority_tally_visible(self) -> bool:
        return bool(self.snapshot.get("majority_tally_visible", False))

    @rx.var
    def kata_majority_tally(self) -> str:
        return str(self.snapshot.get("majority_tally") or "")

    @rx.var
    def kata_is_informal_mode(self) -> bool:
        return str(self.snapshot.get("kata_mode") or "") == "INFORMAL"

    @rx.var
    def kata_informal_athlete_name(self) -> str:
        informal = self.snapshot.get("informal", {})
        if not isinstance(informal, dict):
            return "ATLETA"
        return str(informal.get("athlete_name") or "ATLETA")

    @rx.var
    def kata_informal_results(self) -> list[str]:
        informal = self.snapshot.get("informal", {})
        if not isinstance(informal, dict):
            return []
        raw = informal.get("results", [])
        if not isinstance(raw, list):
            return []
        return [str(item) for item in raw]

    @rx.var
    def kumite_title(self) -> str:
        return str(self.snapshot.get("title") or "Combate en vivo")

    @rx.var
    def kumite_aka_name(self) -> str:
        aka = self.snapshot.get("aka", {})
        return str(aka.get("name") or "ATLETA 1") if isinstance(aka, dict) else "ATLETA 1"

    @rx.var
    def kumite_ao_name(self) -> str:
        ao = self.snapshot.get("ao", {})
        return str(ao.get("name") or "ATLETA 2") if isinstance(ao, dict) else "ATLETA 2"

    @rx.var
    def kumite_aka_score(self) -> str:
        aka = self.snapshot.get("aka", {})
        return str(aka.get("score") or 0) if isinstance(aka, dict) else "0"

    @rx.var
    def kumite_ao_score(self) -> str:
        ao = self.snapshot.get("ao", {})
        return str(ao.get("score") or 0) if isinstance(ao, dict) else "0"

    @rx.var
    def kumite_timer_formatted(self) -> str:
        return str(self.snapshot.get("timer_formatted") or "03:00")

    @rx.var
    def kumite_aka_senshu(self) -> bool:
        aka = self.snapshot.get("aka", {})
        return bool(aka.get("senshu", False)) if isinstance(aka, dict) else False

    @rx.var
    def kumite_ao_senshu(self) -> bool:
        ao = self.snapshot.get("ao", {})
        return bool(ao.get("senshu", False)) if isinstance(ao, dict) else False

    @rx.var
    def kumite_aka_penalties_label(self) -> str:
        aka = self.snapshot.get("aka", {})
        penalties = aka.get("penalties", {}) if isinstance(aka, dict) else {}
        return self._format_penalties_label(penalties)

    @rx.var
    def kumite_ao_penalties_label(self) -> str:
        ao = self.snapshot.get("ao", {})
        penalties = ao.get("penalties", {}) if isinstance(ao, dict) else {}
        return self._format_penalties_label(penalties)

    @staticmethod
    def _format_penalties_label(raw_penalties: object) -> str:
        if not isinstance(raw_penalties, dict):
            return "Ninguna"
        active = [
            key
            for key in ("C1", "C2", "C3", "HC", "H")
            if bool(raw_penalties.get(key, False))
        ]
        if len(active) == 0:
            return "Ninguna"
        return ", ".join(active)

    def _is_viewer_connected(self) -> bool:
        try:
            app = rx.State._get_app()  # type: ignore[attr-defined]
            token = self.router.session.client_token
            socket_record = app._token_manager.token_to_socket.get(token)
            return socket_record is not None
        except Exception:
            return True

    def _route_params(self) -> dict[str, Any]:
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_display_key_param(self) -> str:
        params = self._route_params()
        display_key = str(params.get("display_key", "")).strip()
        if display_key == "":
            raise ValueError("Pantalla no encontrada")
        return display_key

    def _apply_snapshot_payload(self, payload: dict[str, Any]) -> None:
        self.snapshot = payload
        self.has_snapshot = True
        self.modality = str(payload.get("modality", ""))
        self.source_kind = str(payload.get("source_kind", ""))

    @rx.event
    async def load_display(self) -> None:
        self.is_loading = True
        self.error_message = ""
        try:
            self.current_display_key = self._parse_display_key_param()
        except ValueError as error:
            self.current_display_key = ""
            self.snapshot = {}
            self.has_snapshot = False
            self.is_stale = False
            self.error_message = str(error)
            self.is_loading = False
            return

        result = SecondaryDisplayService.read_snapshot(
            display_key=self.current_display_key,
            stale_after_seconds=self.stale_after_seconds,
        )
        if result.status == "missing":
            self.snapshot = {}
            self.has_snapshot = False
            self.is_stale = False
            self.error_message = "Pantalla no encontrada"
            self.is_loading = False
            return

        self._apply_snapshot_payload(result.snapshot or {})
        self.is_stale = result.status == "stale"
        self.is_loading = False

    @rx.event
    async def refresh_snapshot(self) -> None:
        if self.current_display_key == "":
            return

        result = SecondaryDisplayService.read_snapshot(
            display_key=self.current_display_key,
            stale_after_seconds=self.stale_after_seconds,
        )
        if result.status == "missing":
            self.snapshot = {}
            self.has_snapshot = False
            self.is_stale = False
            self.error_message = "Pantalla no encontrada"
            return

        self.error_message = ""
        self._apply_snapshot_payload(result.snapshot or {})
        self.is_stale = result.status == "stale"

    @rx.event(background=True)
    async def poll_snapshot_loop(self) -> None:
        while True:
            async with self:
                is_connected = self._is_viewer_connected()
                display_key = self.current_display_key
                stale_after_seconds = self.stale_after_seconds

            if not is_connected:
                break

            if display_key != "":
                result = SecondaryDisplayService.read_snapshot(
                    display_key=display_key,
                    stale_after_seconds=stale_after_seconds,
                )

                async with self:
                    if result.status == "missing":
                        self.snapshot = {}
                        self.has_snapshot = False
                        self.is_stale = False
                        self.error_message = "Pantalla no encontrada"
                    else:
                        self.error_message = ""
                        self._apply_snapshot_payload(result.snapshot or {})
                        self.is_stale = result.status == "stale"

            await asyncio.sleep(1.0)
