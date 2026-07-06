MOCK_GEOMAP = {
    "new york": [{"municipality": "New York City", "state": "NY", "county": "New York"}],
    "new york city": [{"municipality": "New York City", "state": "NY", "county": "New York"}],
    "nyc": [{"municipality": "New York City", "state": "NY", "county": "New York"}],
    "irvine": [{"municipality": "Irvine", "state": "CA", "county": "Orange"}],
    "los angeles": [{"municipality": "Los Angeles", "state": "CA", "county": "Los Angeles"}],
    "la": [{"municipality": "Los Angeles", "state": "CA", "county": "Los Angeles"}],
    "denver": [{"municipality": "Denver", "state": "CO", "county": "Denver"}],
    "san diego": [{"municipality": "San Diego", "state": "CA", "county": "San Diego"}],
    "steamboat springs": [{"municipality": "Steamboat Springs", "state": "CO", "county": "Routt"}],
    "steamboat": [{"municipality": "Steamboat Springs", "state": "CO", "county": "Routt"}],
    "austin": [{"municipality": "Austin", "state": "TX", "county": "Travis"}],
    "new orleans": [{"municipality": "New Orleans", "state": "LA", "county": "Orleans"}],
    "honolulu": [{"municipality": "Honolulu", "state": "HI", "county": "Honolulu"}],
    "las vegas": [{"municipality": "Las Vegas", "state": "NV", "county": "Clark"}],
    "clark county": [{"municipality": "Clark County", "state": "NV", "county": "Clark"}],
    "gatlinburg": [{"municipality": "Gatlinburg", "state": "TN", "county": "Sevier"}],
    "broken bow": [{"municipality": "Broken Bow", "state": "OK", "county": "McCurtain"}],
    "poconos": [
        {"municipality": "Stroudsburg", "state": "PA", "county": "Monroe"},
        {"municipality": "East Stroudsburg", "state": "PA", "county": "Monroe"}
    ],
    "new hampshire": [
        {"municipality": "Lincoln", "state": "NH", "county": "Grafton"},
        {"municipality": "Conway", "state": "NH", "county": "Carroll"}
    ],
}

MOCK_MASHVISOR_DB = {
    "Gatlinburg": {
        "sample_size": 142,
        "median_property_price": 450000,
        "average_daily_rate_adr": 285,
        "annual_occupancy_rate_percentage": 68,
        "average_cap_rate_percentage": 7.8,
        "active_listings_count": 3450,
        "listings_growth_yoy_percentage": 2.1,
        "revenue_growth_yoy_percentage": 4.2,
        "seasonality_summary": "High — ~60% of revenue between June and October; weakest Nov–Feb.",
        "estimated_opex": {
            "property_management_pct": 15,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 3,
            "bathrooms": 2.5,
            "accommodates": 8
        }
    },
    "Broken Bow": {
        "sample_size": 95,
        "median_property_price": 520000,
        "average_daily_rate_adr": 310,
        "annual_occupancy_rate_percentage": 65,
        "average_cap_rate_percentage": 7.2,
        "active_listings_count": 1200,
        "listings_growth_yoy_percentage": 4.5,
        "revenue_growth_yoy_percentage": 5.8,
        "seasonality_summary": "Moderate — stable occupancy spring through autumn; peak summer.",
        "estimated_opex": {
            "property_management_pct": 18,
            "insurance_pct": 3,
            "utilities_pct": 4,
            "property_taxes_pct": 4
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "accommodates": 10
        }
    },
    "Stroudsburg": {
        "sample_size": 65,
        "median_property_price": 320000,
        "average_daily_rate_adr": 240,
        "annual_occupancy_rate_percentage": 60,
        "average_cap_rate_percentage": 6.8,
        "active_listings_count": 800,
        "listings_growth_yoy_percentage": 3.2,
        "revenue_growth_yoy_percentage": 3.9,
        "seasonality_summary": "High seasonality — summer lake visits and winter ski peaks.",
        "estimated_opex": {
            "property_management_pct": 15,
            "insurance_pct": 4,
            "utilities_pct": 6,
            "property_taxes_pct": 6
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "East Stroudsburg": {
        "sample_size": 45,
        "median_property_price": 310000,
        "average_daily_rate_adr": 230,
        "annual_occupancy_rate_percentage": 58,
        "average_cap_rate_percentage": 6.4,
        "active_listings_count": 600,
        "listings_growth_yoy_percentage": 2.8,
        "revenue_growth_yoy_percentage": 3.1,
        "seasonality_summary": "High seasonality — summer lake visits and winter ski peaks.",
        "estimated_opex": {
            "property_management_pct": 15,
            "insurance_pct": 4,
            "utilities_pct": 6,
            "property_taxes_pct": 6
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "Lincoln": {
        "sample_size": 85,
        "median_property_price": 380000,
        "average_daily_rate_adr": 260,
        "annual_occupancy_rate_percentage": 62,
        "average_cap_rate_percentage": 7.1,
        "active_listings_count": 950,
        "listings_growth_yoy_percentage": 3.5,
        "revenue_growth_yoy_percentage": 4.5,
        "seasonality_summary": "High seasonality — leaf peeping autumn and ski season winter.",
        "estimated_opex": {
            "property_management_pct": 15,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "Conway": {
        "sample_size": 75,
        "median_property_price": 360000,
        "average_daily_rate_adr": 250,
        "annual_occupancy_rate_percentage": 61,
        "average_cap_rate_percentage": 6.9,
        "active_listings_count": 850,
        "listings_growth_yoy_percentage": 3.0,
        "revenue_growth_yoy_percentage": 4.0,
        "seasonality_summary": "High seasonality — leaf peeping autumn and ski season winter.",
        "estimated_opex": {
            "property_management_pct": 15,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "Cabin",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "Los Angeles": {
        "sample_size": 350,
        "median_property_price": 850000,
        "average_daily_rate_adr": 320,
        "annual_occupancy_rate_percentage": 72,
        "average_cap_rate_percentage": 4.8,
        "active_listings_count": 8500,
        "listings_growth_yoy_percentage": 1.2,
        "revenue_growth_yoy_percentage": 2.5,
        "seasonality_summary": "Low seasonality — consistent demand year round due to tourism.",
        "estimated_opex": {
            "property_management_pct": 20,
            "insurance_pct": 3,
            "utilities_pct": 4,
            "property_taxes_pct": 4
        },
        "optimal_config": {
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 2.0,
            "accommodates": 4
        }
    },
    "Denver": {
        "sample_size": 180,
        "median_property_price": 550000,
        "average_daily_rate_adr": 220,
        "annual_occupancy_rate_percentage": 70,
        "average_cap_rate_percentage": 5.2,
        "active_listings_count": 2800,
        "listings_growth_yoy_percentage": 1.8,
        "revenue_growth_yoy_percentage": 3.1,
        "seasonality_summary": "Low to Moderate seasonality — steady business and outdoor travel.",
        "estimated_opex": {
            "property_management_pct": 18,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "House",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "San Diego": {
        "sample_size": 220,
        "median_property_price": 780000,
        "average_daily_rate_adr": 290,
        "annual_occupancy_rate_percentage": 75,
        "average_cap_rate_percentage": 5.6,
        "active_listings_count": 5200,
        "listings_growth_yoy_percentage": 0.8,
        "revenue_growth_yoy_percentage": 2.1,
        "seasonality_summary": "Low seasonality — high demand in summer, mild winters.",
        "estimated_opex": {
            "property_management_pct": 20,
            "insurance_pct": 3,
            "utilities_pct": 4,
            "property_taxes_pct": 4
        },
        "optimal_config": {
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 2.0,
            "accommodates": 4
        }
    },
    "Steamboat Springs": {
        "sample_size": 110,
        "median_property_price": 620000,
        "average_daily_rate_adr": 340,
        "annual_occupancy_rate_percentage": 63,
        "average_cap_rate_percentage": 6.5,
        "active_listings_count": 1400,
        "listings_growth_yoy_percentage": 2.5,
        "revenue_growth_yoy_percentage": 4.1,
        "seasonality_summary": "High seasonality — winter ski dominant, summer mountain biking.",
        "estimated_opex": {
            "property_management_pct": 22,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "Condo",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 8
        }
    },
    "Austin": {
        "sample_size": 260,
        "median_property_price": 580000,
        "average_daily_rate_adr": 250,
        "annual_occupancy_rate_percentage": 64,
        "average_cap_rate_percentage": 5.1,
        "active_listings_count": 6100,
        "listings_growth_yoy_percentage": 2.0,
        "revenue_growth_yoy_percentage": 3.5,
        "seasonality_summary": "Moderate seasonality — peaks during SXSW and Austin City Limits festivals.",
        "estimated_opex": {
            "property_management_pct": 18,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "House",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "New Orleans": {
        "sample_size": 190,
        "median_property_price": 420000,
        "average_daily_rate_adr": 230,
        "annual_occupancy_rate_percentage": 62,
        "average_cap_rate_percentage": 5.4,
        "active_listings_count": 3900,
        "listings_growth_yoy_percentage": 1.5,
        "revenue_growth_yoy_percentage": 2.8,
        "seasonality_summary": "Moderate seasonality — peaks during Mardi Gras and Jazz Fest.",
        "estimated_opex": {
            "property_management_pct": 20,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "House",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "Honolulu": {
        "sample_size": 150,
        "median_property_price": 720000,
        "average_daily_rate_adr": 280,
        "annual_occupancy_rate_percentage": 78,
        "average_cap_rate_percentage": 5.8,
        "active_listings_count": 4800,
        "listings_growth_yoy_percentage": 1.1,
        "revenue_growth_yoy_percentage": 2.3,
        "seasonality_summary": "Low seasonality — high year-round demand from global travelers.",
        "estimated_opex": {
            "property_management_pct": 20,
            "insurance_pct": 3,
            "utilities_pct": 4,
            "property_taxes_pct": 4
        },
        "optimal_config": {
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 2.0,
            "accommodates": 4
        }
    },
    "Las Vegas": {
        "sample_size": 310,
        "median_property_price": 410000,
        "average_daily_rate_adr": 210,
        "annual_occupancy_rate_percentage": 66,
        "average_cap_rate_percentage": 5.9,
        "active_listings_count": 5500,
        "listings_growth_yoy_percentage": 2.2,
        "revenue_growth_yoy_percentage": 3.8,
        "seasonality_summary": "Low seasonality — consistent entertainment-driven tourism.",
        "estimated_opex": {
            "property_management_pct": 18,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "House",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    },
    "Clark County": {
        "sample_size": 280,
        "median_property_price": 390000,
        "average_daily_rate_adr": 200,
        "annual_occupancy_rate_percentage": 64,
        "average_cap_rate_percentage": 5.7,
        "active_listings_count": 4500,
        "listings_growth_yoy_percentage": 2.0,
        "revenue_growth_yoy_percentage": 3.4,
        "seasonality_summary": "Low seasonality — consistent entertainment-driven tourism.",
        "estimated_opex": {
            "property_management_pct": 18,
            "insurance_pct": 3,
            "utilities_pct": 5,
            "property_taxes_pct": 5
        },
        "optimal_config": {
            "property_type": "House",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "accommodates": 6
        }
    }
}
