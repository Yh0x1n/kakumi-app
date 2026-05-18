"""Unit tests for enum translation functions (ES ↔ EN) in states & services."""

from kakumi_app.states.athlete_state import AthleteState
from kakumi_app.states.referee_state import RefereeState
from kakumi_app.services.import_service import ImportService


class TestGenderTranslation:
    """AthleteState gender translation: _normalize_gender / _display_gender."""

    def test_normalize_gender_masculino_to_male(self) -> None:
        assert AthleteState._normalize_gender("MASCULINO") == "MALE"

    def test_normalize_gender_femenino_to_female(self) -> None:
        assert AthleteState._normalize_gender("FEMENINO") == "FEMALE"

    def test_normalize_gender_english_passthrough(self) -> None:
        assert AthleteState._normalize_gender("MALE") == "MALE"
        assert AthleteState._normalize_gender("FEMALE") == "FEMALE"

    def test_normalize_gender_lowercase_input(self) -> None:
        assert AthleteState._normalize_gender("masculino") == "MALE"
        assert AthleteState._normalize_gender("femenino") == "FEMALE"

    def test_normalize_gender_empty_fallback(self) -> None:
        assert AthleteState._normalize_gender("") == "MALE"

    def test_normalize_gender_whitespace(self) -> None:
        assert AthleteState._normalize_gender("  MASCULINO  ") == "MALE"

    def test_display_gender_male_to_masculino(self) -> None:
        assert AthleteState._display_gender("MALE") == "MASCULINO"

    def test_display_gender_female_to_femenino(self) -> None:
        assert AthleteState._display_gender("FEMALE") == "FEMENINO"

    def test_display_gender_round_trip(self) -> None:
        """MASCULINO → normalize → MALE → display → MASCULINO"""
        assert AthleteState._display_gender(
            AthleteState._normalize_gender("MASCULINO")
        ) == "MASCULINO"


class TestRefereeLicenseLevelTranslation:
    """RefereeState license_level translation functions."""

    def test_normalize_license_level_nacional(self) -> None:
        assert RefereeState._normalize_license_level("NACIONAL") == "NATIONAL"

    def test_normalize_license_level_internacional(self) -> None:
        assert RefereeState._normalize_license_level("INTERNACIONAL") == "INTERNATIONAL"

    def test_normalize_license_level_english_passthrough(self) -> None:
        assert RefereeState._normalize_license_level("NATIONAL") == "NATIONAL"
        assert RefereeState._normalize_license_level("INTERNATIONAL") == "INTERNATIONAL"

    def test_display_license_level_national(self) -> None:
        assert RefereeState._display_license_level("NATIONAL") == "NACIONAL"

    def test_display_license_level_international(self) -> None:
        assert RefereeState._display_license_level("INTERNATIONAL") == "INTERNACIONAL"

    def test_normalize_lowercase(self) -> None:
        assert RefereeState._normalize_license_level("nacional") == "NATIONAL"

    def test_license_level_round_trip(self) -> None:
        assert RefereeState._display_license_level(
            RefereeState._normalize_license_level("INTERNACIONAL")
        ) == "INTERNACIONAL"


class TestRefereeRoleTranslation:
    """RefereeState role translation functions."""

    def test_normalize_role_referee(self) -> None:
        assert RefereeState._normalize_role("REFEREE") == "REFEREE"

    def test_normalize_role_juez(self) -> None:
        assert RefereeState._normalize_role("JUEZ") == "JUDGE"

    def test_normalize_role_oficial_de_mesa(self) -> None:
        assert RefereeState._normalize_role("OFICIAL DE MESA") == "TABLE_OFFICIAL"

    def test_normalize_role_supervisor_kansa(self) -> None:
        assert RefereeState._normalize_role("SUPERVISOR (KANSA)") == "SUPERVISOR"

    def test_normalize_role_english_passthrough(self) -> None:
        assert RefereeState._normalize_role("JUDGE") == "JUDGE"
        assert RefereeState._normalize_role("TABLE_OFFICIAL") == "TABLE_OFFICIAL"
        assert RefereeState._normalize_role("SUPERVISOR") == "SUPERVISOR"

    def test_display_role_referee(self) -> None:
        assert RefereeState._display_role("REFEREE") == "REFEREE"

    def test_display_role_judge(self) -> None:
        assert RefereeState._display_role("JUDGE") == "JUEZ"

    def test_display_role_table_official(self) -> None:
        assert RefereeState._display_role("TABLE_OFFICIAL") == "OFICIAL DE MESA"

    def test_display_role_supervisor(self) -> None:
        assert RefereeState._display_role("SUPERVISOR") == "SUPERVISOR (KANSA)"


class TestImportServiceGenderValidation:
    """ImportService.validate_gender with Spanish values."""

    def test_validate_gender_accepts_masculino(self) -> None:
        assert ImportService.validate_gender("MASCULINO") is True

    def test_validate_gender_accepts_femenino(self) -> None:
        assert ImportService.validate_gender("FEMENINO") is True

    def test_validate_gender_accepts_male(self) -> None:
        assert ImportService.validate_gender("MALE") is True

    def test_validate_gender_accepts_female(self) -> None:
        assert ImportService.validate_gender("FEMALE") is True

    def test_validate_gender_rejects_invalid(self) -> None:
        assert ImportService.validate_gender("OTHER") is False
        assert ImportService.validate_gender("") is False


class TestImportServiceParseAthleteRowGender:
    """ImportService.parse_athlete_row with Spanish gender values."""

    def test_parse_athlete_row_with_masculino(self) -> None:
        success, data, _ = ImportService.parse_athlete_row(
            {
                "name": "Test Athlete",
                "date_of_birth": "2000-01-01",
                "gender": "MASCULINO",
            },
            2,
        )
        assert success is True
        assert data is not None
        assert data["gender"] == "MALE"

    def test_parse_athlete_row_with_femenino(self) -> None:
        success, data, _ = ImportService.parse_athlete_row(
            {
                "name": "Test Female",
                "date_of_birth": "2000-01-01",
                "gender": "FEMENINO",
            },
            3,
        )
        assert success is True
        assert data is not None
        assert data["gender"] == "FEMALE"

    def test_parse_athlete_row_with_male(self) -> None:
        success, data, _ = ImportService.parse_athlete_row(
            {
                "name": "Test EN",
                "date_of_birth": "2000-01-01",
                "gender": "MALE",
            },
            4,
        )
        assert success is True
        assert data is not None
        assert data["gender"] == "MALE"

    def test_parse_athlete_row_rejects_invalid_gender(self) -> None:
        success, data, error = ImportService.parse_athlete_row(
            {
                "name": "Test Bad",
                "date_of_birth": "2000-01-01",
                "gender": "OTHER",
            },
            5,
        )
        assert success is False
        assert data is None
        assert "gender" in error.lower()


class TestImportServiceRefereeRowSpanish:
    """ImportService._parse_referee_row with Spanish values."""

    def test_parse_referee_row_nacional(self) -> None:
        data, error = ImportService._parse_referee_row(
            {
                "name": "Ref Español",
                "license_number": "LIC-ES-001",
                "license_level": "NACIONAL",
                "role": "JUEZ",
                "is_available": "true",
            },
            2,
            {"NATIONAL", "INTERNATIONAL", "NACIONAL", "INTERNACIONAL"},
            {"REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR", "JUEZ", "OFICIAL DE MESA", "SUPERVISOR (KANSA)"},
        )
        assert error is None
        assert data is not None
        assert data["license_level"] == "NATIONAL"
        assert data["role"] == "JUDGE"

    def test_parse_referee_row_internacional_oficial_mesa(self) -> None:
        data, error = ImportService._parse_referee_row(
            {
                "name": "Ref Ofi Mesa",
                "license_number": "LIC-ES-002",
                "license_level": "INTERNACIONAL",
                "role": "OFICIAL DE MESA",
                "is_available": "true",
            },
            3,
            {"NATIONAL", "INTERNATIONAL", "NACIONAL", "INTERNACIONAL"},
            {"REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR", "JUEZ", "OFICIAL DE MESA", "SUPERVISOR (KANSA)"},
        )
        assert error is None
        assert data is not None
        assert data["license_level"] == "INTERNATIONAL"
        assert data["role"] == "TABLE_OFFICIAL"

    def test_parse_referee_row_supervisor_kansa(self) -> None:
        data, error = ImportService._parse_referee_row(
            {
                "name": "Ref Supervisor",
                "license_number": "LIC-ES-003",
                "license_level": "NACIONAL",
                "role": "SUPERVISOR (KANSA)",
                "is_available": "true",
            },
            4,
            {"NATIONAL", "INTERNATIONAL", "NACIONAL", "INTERNACIONAL"},
            {"REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR", "JUEZ", "OFICIAL DE MESA", "SUPERVISOR (KANSA)"},
        )
        assert error is None
        assert data is not None
        assert data["license_level"] == "NATIONAL"
        assert data["role"] == "SUPERVISOR"

    def test_parse_referee_row_english_still_works(self) -> None:
        data, error = ImportService._parse_referee_row(
            {
                "name": "Ref English",
                "license_number": "LIC-EN-001",
                "license_level": "INTERNATIONAL",
                "role": "REFEREE",
                "is_available": "true",
            },
            5,
            {"NATIONAL", "INTERNATIONAL", "NACIONAL", "INTERNACIONAL"},
            {"REFEREE", "JUDGE", "TABLE_OFFICIAL", "SUPERVISOR", "JUEZ", "OFICIAL DE MESA", "SUPERVISOR (KANSA)"},
        )
        assert error is None
        assert data is not None
        assert data["license_level"] == "INTERNATIONAL"
        assert data["role"] == "REFEREE"
