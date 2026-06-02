# Tasks for Phase 2: Eliminar warnings de cliente desconectado

## Implementación del registro de visualizadores
- [ ] Crear atributo estático `_viewer_registry: dict[str, set[str]]` en `kakumi_app/services/secondary_display_service.py`.
- [ ] Añadir método `register_viewer(self, display_key: str, token: str) -> None`.
- [ ] Añadir método `unregister_viewer(self, display_key: str, token: str) -> None`.
- [ ] Añadir método `has_active_viewers(self, display_key: str) -> bool`.
- [ ] Añadir método `unregister_viewer_by_token(self, token: str) -> None`.

## Integración en el estado de visualización
- [ ] En `kakumi_app/states/secondary_display_state.py` llamar a `register_viewer` al cargar la pantalla.
- [ ] Gestionar desconexiones llamando a `unregister_viewer` o `unregister_viewer_by_token`.

## Guardas en la publicación de snapshots
- [ ] Modificar `kakumi_app/states/kata_match_state.py` para que `_publish_display_snapshot` verifique `has_active_viewers` antes de publicar.
- [ ] Modificar `kakumi_app/states/kumite_match_state.py` en `_publish_display_snapshot` y `_publish_display_snapshot_background_safe` con la misma verificación.

## Pruebas (TDD)
- [ ] Añadir pruebas unitarias para los métodos del registro (registro, desregistro, consulta).
- [ ] Añadir pruebas que verifiquen que `_publish_display_snapshot` se omite cuando no hay visualizadores activos.
- [ ] Añadir pruebas que verifiquen que los snapshots se publican normalmente cuando hay al menos un visualizador.
- [ ] Configurar fixture `autouse` en `tests/conftest.py` para forzar `has_active_viewers` a `True` salvo en los tests específicos de este cambio.

## Progreso
- [ ] Actualizar `openspec/changes/disconnected-client-warnings/apply-progress.md` con evidencia TDD.
