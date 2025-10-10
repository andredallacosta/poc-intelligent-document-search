from datetime import datetime

import pytest

from domain.entities.municipality import Municipality
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.municipality_id import MunicipalityId


class TestMunicipality:
    def test_create_valid_municipality(self):
        municipality_id = MunicipalityId.generate()
        municipality = Municipality(
            id=municipality_id, name="São Paulo Municipality", token_quota=10000
        )
        assert municipality.id == municipality_id
        assert municipality.name == "São Paulo Municipality"
        assert municipality.token_quota == 10000
        assert municipality.tokens_consumed == 0
        assert municipality.active is True
        assert isinstance(municipality.created_at, datetime)
        assert isinstance(municipality.updated_at, datetime)

    def test_create_municipality_factory_method(self):
        municipality = Municipality.create(
            "Rio de Janeiro Municipality", token_quota=5000
        )
        assert municipality.name == "Rio de Janeiro Municipality"
        assert municipality.token_quota == 5000
        assert municipality.tokens_consumed == 0
        assert municipality.active is True
        assert isinstance(municipality.id, MunicipalityId)

    def test_create_municipality_factory_method_defaults(self):
        municipality = Municipality.create("Brasília Municipality")
        assert municipality.name == "Brasília Municipality"
        assert municipality.token_quota == 10000
        assert municipality.active is True

    def test_empty_name_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Municipality name is required"
        ):
            Municipality(id=municipality_id, name="", token_quota=10000)

    def test_whitespace_only_name_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Municipality name is required"
        ):
            Municipality(id=municipality_id, name="   ", token_quota=10000)

    def test_name_too_long_raises_error(self):
        municipality_id = MunicipalityId.generate()
        long_name = "A" * 256
        with pytest.raises(
            BusinessRuleViolationError,
            match="Municipality name cannot exceed 255 characters",
        ):
            Municipality(id=municipality_id, name=long_name, token_quota=10000)

    def test_negative_quota_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Token quota cannot be negative"
        ):
            Municipality(
                id=municipality_id, name="Test Municipality", token_quota=-1000
            )

    def test_negative_tokens_consumed_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Tokens consumed cannot be negative"
        ):
            Municipality(
                id=municipality_id,
                name="Test Municipality",
                token_quota=10000,
                tokens_consumed=-100,
            )

    def test_tokens_consumed_exceeds_quota_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Tokens consumed cannot exceed quota"
        ):
            Municipality(
                id=municipality_id,
                name="Test Municipality",
                token_quota=10000,
                tokens_consumed=15000,
            )

    def test_negative_monthly_limit_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Monthly limit must be positive"
        ):
            Municipality(
                id=municipality_id,
                name="Test Municipality",
                token_quota=10000,
                monthly_token_limit=0,
            )

    def test_monthly_limit_too_high_raises_error(self):
        municipality_id = MunicipalityId.generate()
        with pytest.raises(
            BusinessRuleViolationError, match="Monthly limit cannot exceed 1M tokens"
        ):
            Municipality(
                id=municipality_id,
                name="Test Municipality",
                token_quota=10000,
                monthly_token_limit=1000001,
            )

    def test_future_contract_date_raises_error(self):
        from datetime import date, timedelta

        municipality_id = MunicipalityId.generate()
        future_date = date.today() + timedelta(days=1)
        with pytest.raises(
            BusinessRuleViolationError, match="Contract date cannot be in the future"
        ):
            Municipality(
                id=municipality_id,
                name="Test Municipality",
                token_quota=10000,
                contract_date=future_date,
            )

    def test_consume_tokens_valid(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.consume_tokens(5000)
        assert municipality.tokens_consumed == 5000
        assert municipality.remaining_tokens == 5000

    def test_consume_tokens_exceeds_quota_raises_error(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        with pytest.raises(BusinessRuleViolationError, match="Token quota exceeded"):
            municipality.consume_tokens(15000)

    def test_consume_negative_tokens_raises_error(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        with pytest.raises(
            BusinessRuleViolationError, match="Token amount must be positive"
        ):
            municipality.consume_tokens(-1000)

    def test_increase_quota_valid(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.consume_tokens(3000)
        municipality.increase_quota(15000)
        assert municipality.token_quota == 15000
        assert municipality.tokens_consumed == 3000
        assert municipality.remaining_tokens == 12000

    def test_increase_quota_below_consumed_raises_error(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.consume_tokens(5000)
        with pytest.raises(
            BusinessRuleViolationError,
            match="New quota.*cannot be less than already consumed tokens",
        ):
            municipality.increase_quota(3000)

    def test_reset_consumption(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.consume_tokens(5000)
        municipality.reset_consumption()
        assert municipality.tokens_consumed == 0
        assert municipality.remaining_tokens == 10000

    def test_deactivate(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.deactivate()
        assert municipality.active is False

    def test_activate(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.deactivate()
        municipality.activate()
        assert municipality.active is True

    def test_remaining_tokens_calculation(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.remaining_tokens == 10000
        municipality.consume_tokens(3000)
        assert municipality.remaining_tokens == 7000
        municipality.consume_tokens(7000)
        assert municipality.remaining_tokens == 0

    def test_consumption_percentage_calculation(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.consumption_percentage == 0.0
        municipality.consume_tokens(2500)
        assert municipality.consumption_percentage == 25.0
        municipality.consume_tokens(2500)
        assert municipality.consumption_percentage == 50.0
        municipality.consume_tokens(5000)
        assert municipality.consumption_percentage == 100.0

    def test_quota_exhausted_property(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.quota_exhausted is False
        municipality.consume_tokens(10000)
        assert municipality.quota_exhausted is True

    def test_quota_critical_property(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.quota_critical is False
        municipality.consume_tokens(9000)
        assert municipality.quota_critical is False
        municipality.consume_tokens(100)
        assert municipality.quota_critical is True

    def test_can_consume_valid(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.can_consume(5000) is True
        assert municipality.can_consume(10000) is True
        assert municipality.can_consume(15000) is False

    def test_can_consume_inactive_municipality(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.deactivate()
        assert municipality.can_consume(1000) is False

    def test_update_monthly_limit_valid(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.update_monthly_limit(50000)
        assert municipality.monthly_token_limit == 50000

    def test_update_monthly_limit_negative_raises_error(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        with pytest.raises(
            BusinessRuleViolationError, match="New limit must be positive"
        ):
            municipality.update_monthly_limit(0)

    def test_update_monthly_limit_too_high_raises_error(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        with pytest.raises(
            BusinessRuleViolationError, match="Limit cannot exceed 1M tokens"
        ):
            municipality.update_monthly_limit(1000001)

    def test_can_renew_period_active(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        assert municipality.can_renew_period() is True

    def test_can_renew_period_inactive(self):
        municipality = Municipality.create("Test Municipality", token_quota=10000)
        municipality.deactivate()
        assert municipality.can_renew_period() is False

    def test_calculate_next_due_date(self):
        from datetime import date

        municipality = Municipality.create("Test Municipality", token_quota=10000)
        next_due = municipality.calculate_next_due_date()
        assert isinstance(next_due, date)
        assert next_due > date.today()
