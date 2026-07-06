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

def calculate_annual_revenue(adr: float, occupancy_rate_pct: float) -> int:
    """Calculates estimated annual revenue."""
    return int(adr * 365 * (occupancy_rate_pct / 100.0))

def calculate_opex_breakdown(annual_revenue: int, opex_pct: dict) -> tuple[dict, int, float]:
    """Calculates standard OpEx breakdown and totals.

    Returns:
        tuple containing:
            - breakdown dict containing annual cost and percentage for each category
            - total annual opex amount
            - total opex percentage of revenue
    """
    pm_pct = opex_pct.get("property_management_pct", 0.0)
    ins_pct = opex_pct.get("insurance_pct", 0.0)
    util_pct = opex_pct.get("utilities_pct", 0.0)
    tax_pct = opex_pct.get("property_taxes_pct", 0.0)

    pm_val = int(annual_revenue * (pm_pct / 100.0))
    ins_val = int(annual_revenue * (ins_pct / 100.0))
    util_val = int(annual_revenue * (util_pct / 100.0))
    tax_val = int(annual_revenue * (tax_pct / 100.0))

    breakdown = {
        "property_management": {"annual": pm_val, "percentage_of_revenue": pm_pct},
        "insurance": {"annual": ins_val, "percentage_of_revenue": ins_pct},
        "utilities": {"annual": util_val, "percentage_of_revenue": util_pct},
        "property_taxes": {"annual": tax_val, "percentage_of_revenue": tax_pct}
    }

    total_annual_opex = pm_val + ins_val + util_val + tax_val
    total_opex_pct = pm_pct + ins_pct + util_pct + tax_pct

    return breakdown, total_annual_opex, total_opex_pct

def calculate_noi(annual_revenue: int, total_annual_opex: int) -> int:
    """Calculates Net Operating Income (NOI)."""
    return annual_revenue - total_annual_opex

def calculate_cap_rate(noi: int, median_price: int) -> float:
    """Calculates the average cap rate percentage."""
    if median_price <= 0:
        return 0.0
    return round((noi / median_price) * 100.0, 1)
