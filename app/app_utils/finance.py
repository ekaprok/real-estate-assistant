def determine_data_quality(sample_size: int) -> str:
    """Categorizes the data quality based on the sample size."""
    if sample_size >= 80:
        return "high"
    elif sample_size >= 30:
        return "medium"
    elif sample_size >= 15:
        return "low"
    else:
        return "very_low"

def calculate_annual_revenue(monthly_rental_income: float) -> int:
    """Annualizes Mashvisor's median monthly Airbnb rental income."""
    return int(round(monthly_rental_income * 12))

def calculate_noi(cap_rate_percentage: float, median_price: int) -> int:
    """Derives annual NOI from Mashvisor's cap rate and median price.

    Cap rate is defined as NOI / property price, so NOI = (cap_rate / 100) * price.
    This keeps NOI grounded in fields Mashvisor actually returns rather than a
    fabricated operating-expense breakdown.
    """
    return int(round((cap_rate_percentage / 100.0) * median_price))
