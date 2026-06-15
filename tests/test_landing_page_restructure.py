"""RED→GREEN tests for landing-page-flow restructure (Worker A scope).

RED: these tests MUST FAIL before implementation.
GREEN: after implementation, all MUST PASS.

Files under test:
  - kakumi_app/kakumi_app.py
  - kakumi_app/components/sidebar.py
  - kakumi_app/components/protected_layout.py
"""

from __future__ import annotations


import pytest
import reflex as rx


def test_dashboard_function_exists_after_rename():
    """RED: dashboard() does NOT exist yet (fails now).
    GREEN: after rename from index→dashboard, this passes.
    """
    import kakumi_app.kakumi_app as app_mod

    # This assertion FAILS in RED state — dashboard() hasn't been created yet
    assert hasattr(app_mod, "dashboard"), (
        "RED: dashboard() should not exist yet. "
        "After rename from index() to dashboard(), this will pass."
    )
    assert callable(app_mod.dashboard)


def test_index_returns_landing_page_not_dashboard():
    """RED: index() still returns dashboard content (fails now).
    GREEN: after restructure, index() returns landing page with 'Iniciar Sesión'.
    """
    import kakumi_app.kakumi_app as app_mod

    component = app_mod.index()
    assert isinstance(component, rx.Component), "index() must return a Component"

    # Render to string to inspect content
    rendered_str = str(component.render())

    # GREEN: index() returns landing page with brand name + CTA
    assert "Kakumi" in rendered_str, "index() must contain brand name 'Kakumi'"
    assert "Gesti" in rendered_str, (
        "index() must contain tagline 'Gestión de torneos de Karate-Do'"
    )
    assert "Iniciar" in rendered_str, "index() must contain CTA button 'Iniciar Sesión'"

    # GREEN: index() must NOT contain old dashboard content
    assert "Welcome to Kakumi Tournament Manager" not in rendered_str, (
        "index() must not contain dashboard content after restructure"
    )


def test_dashboard_contains_old_index_content():
    """GREEN: dashboard() must contain the old index() dashboard content."""
    import kakumi_app.kakumi_app as app_mod

    # Skip if dashboard doesn't exist yet (RED state)
    if not hasattr(app_mod, "dashboard"):
        pytest.skip("dashboard() not yet defined (RED state)")

    component = app_mod.dashboard()
    assert isinstance(component, rx.Component), "dashboard() must return a Component"

    rendered_str = str(component.render())

    # Must contain the old dashboard heading
    assert "Welcome to Kakumi Tournament Manager" in rendered_str, (
        "dashboard() must contain the original dashboard heading"
    )
    # Must still use DEV_AUTH_BYPASS guard — verify by checking the source
    import inspect

    source = inspect.getsource(app_mod.dashboard)
    assert "DEV_AUTH_BYPASS" in source, (
        "dashboard() must preserve the DEV_AUTH_BYPASS guard"
    )


def test_dashboard_route_registered():
    """GREEN: app.add_page with dashboard route=/home must exist."""
    import kakumi_app.kakumi_app as app_mod

    # Check source for the route registration
    import inspect

    source = inspect.getsource(app_mod)

    assert 'route="/home"' in source, (
        "GREEN: dashboard must be registered with route='/home'"
    )
    assert "on_load=AuthState.check_auth_redirect" in source, (
        "dashboard route must have auth guard"
    )


def test_landing_route_no_on_load():
    """GREEN: landing page app.add_page must NOT have on_load."""
    import kakumi_app.kakumi_app as app_mod

    import inspect

    source = inspect.getsource(app_mod)

    # Find the app.add_page for index — must not have on_load
    # The landing page registration is:
    #   app.add_page(
    #       index, title="Kakumi"
    #   )
    assert 'index, title="Kakumi"' in source, (
        "Must find app.add_page for index route with title='Kakumi'"
    )

    # Verify on_load is NOT in the landing page registration block
    # Find the index registration by scanning for 'index,' with the new title
    idx = source.find('index, title="Kakumi"')
    assert idx != -1, "index route registration not found"
    # Look backwards for the app.add_page( call
    line_start = source.rfind("\n", 0, idx)
    block_start = source.rfind("\n", 0, line_start - 1)
    block = source[block_start : idx + 30]
    assert "on_load" not in block, "Landing page route must NOT have on_load parameter"


def test_sidebar_href_home():
    """GREEN: sidebar Kakumi brand link must use href='/home'."""
    with open("kakumi_app/components/sidebar.py") as f:
        content = f.read()

    assert 'href="/home"' in content, "sidebar Kakumi link must use href='/home'"
    # Must not have old '/"' href for the brand link
    # (check it's not the old value on line ~177)
    import re

    # Count all href="/" occurrences — should be 0 or only in other links
    old_hrefs = re.findall(r'href="/"', content)
    assert len(old_hrefs) == 0, (
        f"Found {len(old_hrefs)} stale href='/' references in sidebar"
    )


def test_protected_layout_redirect_home():
    """GREEN: protected_layout Go Home must redirect to '/home'."""
    with open("kakumi_app/components/protected_layout.py") as f:
        content = f.read()

    assert 'redirect("/home")' in content, "protected_layout must redirect to '/home'"
    assert 'redirect("/")' not in content, (
        "protected_layout must NOT redirect to plain '/'"
    )
