"""Unit tests for the deterministic financial helpers in ``app.app_utils.finance``.

All figures the report shows are either returned directly by Mashvisor's
``city/investment`` endpoint or derived here, so these calculations are the
last line of defense against silently wrong financials.
"""

import pytest

from app.app_utils.finance import (
    calculate_annual_revenue,
    calculate_noi,
    determine_data_quality,
)


class TestDetermineDataQuality:
    @pytest.mark.parametrize(
        "sample_size, expected",
        [
            (80, "high"),
            (200, "high"),
            (79, "medium"),
            (30, "medium"),
            (29, "low"),
            (15, "low"),
            (14, "very_low"),
            (0, "very_low"),
        ],
    )
    def test_thresholds(self, sample_size, expected):
        assert determine_data_quality(sample_size) == expected


class TestCalculateAnnualRevenue:
    def test_annualizes_monthly_income(self):
        assert calculate_annual_revenue(4000) == 48000

    def test_rounds_to_nearest_dollar(self):
        # 5895.75 * 12 = 70749.0 -> exact
        assert calculate_annual_revenue(5895.75) == 70749
        # 4000.4 * 12 = 48004.8 -> rounds to 48005
        assert calculate_annual_revenue(4000.4) == 48005

    def test_zero_income(self):
        assert calculate_annual_revenue(0) == 0


class TestCalculateNoi:
    def test_derives_from_cap_rate_and_price(self):
        # NOI = (cap_rate / 100) * price -> 6% of 500000
        assert calculate_noi(6.0, 500000) == 30000

    def test_rounds_to_nearest_dollar(self):
        # 7.4% of 450000 = 33300.0
        assert calculate_noi(7.4, 450000) == 33300
        # 5.7% of 390000 = 22230.0
        assert calculate_noi(5.7, 390000) == 22230

    def test_zero_price_yields_zero(self):
        assert calculate_noi(6.0, 0) == 0

    def test_zero_cap_rate_yields_zero(self):
        assert calculate_noi(0.0, 500000) == 0
