MOCK_SEARCH_RESULTS = {
    "new york": {
        "organic": [
            {
                "title": "New York City Short-Term Rental Rules",
                "link": "https://www.nyc.gov/site/specialenforcement/registration-law/registration-law-for-hosts.page",
                "snippet": "Local Law 18 (Short-Term Rental Registration Law) strictly prohibits short-term rentals under 30 days unless the host is present. Unhosted short term rentals are fully banned."
            },
            {
                "title": "Municode: New York City Zoning Resolution",
                "link": "https://municode.com/nyc/zoning-code",
                "snippet": "Zoning regulations restrict transient occupancy of residential units. Under Local Law 18, all STRs must be registered with the Office of Special Enforcement."
            }
        ]
    },
    "irvine": {
        "organic": [
            {
                "title": "Irvine Municipal Code Section 2-37-3",
                "link": "https://www.cityofirvine.org/zoning-ordinance/short-term-rentals",
                "snippet": "Irvine zoning regulations enforce an absolute prohibition of short-term rentals in all residential zones. Operating an STR is illegal in Irvine, CA."
            }
        ]
    },
    "los angeles": {
        "organic": [
            {
                "title": "Los Angeles Home Sharing Ordinance",
                "link": "https://planning.lacity.org/plans-policies/initiative-programs/home-sharing-ordinance",
                "snippet": "Short-term rentals are restricted and permitted only in the host's primary residence. Hosts must live in the property at least 6 months per year. Investment property STRs are banned."
            }
        ]
    },
    "denver": {
        "organic": [
            {
                "title": "Denver Short-Term Rental Licensing",
                "link": "https://www.denvergov.org/Government/Agencies/Business-Licensing/Short-Term-Rentals",
                "snippet": "Denver short-term rentals are restricted and permitted only in the host's primary residence. A host must provide proof of primary residence (voter registration, tax forms)."
            }
        ]
    },
    "san diego": {
        "organic": [
            {
                "title": "San Diego Short-Term Residential Occupancy",
                "link": "https://www.sandiego.gov/treasurer/short-term-residential-occupancy",
                "snippet": "San Diego operates a Tier system with permit caps and a lottery process. Tier 3 (whole home rentals) is capped at 1% of housing stock, requiring a lottery."
            }
        ]
    },
    "steamboat": {
        "organic": [
            {
                "title": "Steamboat Springs Short-Term Rental Regulations",
                "link": "https://www.steamboatsprings.net/str",
                "snippet": "Steamboat Springs manages STRs via an Overlay Zone. Zone Green has unlimited permits, Yellow has permit caps and lottery, Red prohibits STRs completely."
            }
        ]
    },
    "austin": {
        "organic": [
            {
                "title": "Austin Short-Term Rental Licensing",
                "link": "https://www.austintexas.gov/str",
                "snippet": "Austin regulates STRs by type. Type 1 is owner-occupied. Type 2 (non-owner occupied) STRs are strictly limited by zoning overlays or banned in residential zones."
            }
        ]
    },
    "new orleans": {
        "organic": [
            {
                "title": "New Orleans Short-Term Rental Administration",
                "link": "https://nola.gov/short-term-rentals",
                "snippet": "New Orleans NSTR (Residential) permits require owner-occupancy (homestead exemption) and face block density caps. CSTR (Commercial) requires conditional use."
            }
        ]
    },
    "honolulu": {
        "organic": [
            {
                "title": "Honolulu Ordinance 25-02 STR Rules",
                "link": "https://www.honolulu.gov/dpp/str.html",
                "snippet": "Ordinance 25-02 enforces a 90-day minimum stay for most residential areas in Honolulu. Exceptions exist only for grandfathered NUCs or resort zones."
            }
        ]
    },
    "yurt": {
        "organic": [
            {
                "title": "Zoning Code for Temporary Structures and Unique Stays",
                "link": "https://ecode360.com/zoning-temporary-structures",
                "snippet": "Temporary structures like Yurts, RVs, tents, and shipping containers are generally prohibited for short-term rental use even if standard STRs are allowed."
            }
        ]
    },
    "rv": {
        "organic": [
            {
                "title": "Zoning Code for Temporary Structures and Unique Stays",
                "link": "https://ecode360.com/zoning-temporary-structures",
                "snippet": "Temporary structures like Yurts, RVs, tents, and shipping containers are generally prohibited for short-term rental use even if standard STRs are allowed."
            }
        ]
    },
    "las vegas": {
        "organic": [
            {
                "title": "Las Vegas City Short-Term Rental Ordinance",
                "link": "https://www.lasvegasnevada.gov/str",
                "snippet": "Within Las Vegas city limits, STRs require owner-occupancy. In unincorporated Clark County, there are strict distance caps (1000 ft from another STR) and lottery moratoriums."
            }
        ]
    },
    "gatlinburg": {
        "organic": [
            {
                "title": "Gatlinburg Short-Term Rental Permit Office",
                "link": "https://www.gatlinburgtn.gov/departments/finance/business_licenses.php",
                "snippet": "Gatlinburg is highly STR-friendly. Requires a Tourist Accommodation Permit, annual fire inspection, business license, and payment of combined gross receipts tax rate of 9.75%."
            }
        ]
    },
    "broken bow": {
        "organic": [
            {
                "title": "Broken Bow Municipal Code STR Permits",
                "link": "https://www.brokenbowok.gov/str-licensing",
                "snippet": "Broken Bow is STR-friendly with straightforward compliance requirements. Requires registration, local lodging tax, and standard safety compliance."
            }
        ]
    },
    "poconos": {
        "organic": [
            {
                "title": "Poconos STR Rules and Zoning Overlays",
                "link": "https://www.monroecounty.pa.gov/str",
                "snippet": "STRs are permitted in designated tourist overlays and commercial zones. General R-1 residential zones outside overlays are prohibited."
            }
        ]
    },
    "new hampshire": {
        "organic": [
            {
                "title": "New Hampshire Local Zoning for Short-Term Rentals",
                "link": "https://www.nh.gov/local-rules-str",
                "snippet": "Lincoln and Conway permit STRs subject to a local permit and fire safety inspections. No primary residence requirement or caps exist."
            }
        ]
    }
}

MOCK_PAGES = {
    "https://www.nyc.gov/site/specialenforcement/registration-law/registration-law-for-hosts.page": (
        "New York City Short-Term Rental Registration Law (Local Law 18). "
        "Under Local Law 18, short-term rentals (rentals for fewer than 30 consecutive days) "
        "are strictly prohibited unless the host is residing in the unit and the guests have access "
        "to all parts of the unit. Unhosted short-term rentals are completely banned. "
        "Violations carry significant fines starting at $1,000."
    ),
    "https://municode.com/nyc/zoning-code": (
        "New York City Zoning Resolution Chapter 2. Section 22-18. "
        "Transient occupancy of residential apartments is prohibited. Under the administrative code "
        "and Local Law 18, all short-term rental hosts must obtain a registration number. "
        "Unhosted rentals for under 30 days are prohibited."
    ),
    "https://www.cityofirvine.org/zoning-ordinance/short-term-rentals": (
        "City of Irvine Zoning Ordinance Section 2-37-3. "
        "Short-term rentals (less than 30 days) are prohibited in all residential zoning districts "
        "in the City of Irvine. It is unlawful to operate or advertise an STR in any residential zone. "
        "No permits are issued; enforcement is active with daily penalties."
    ),
    "https://planning.lacity.org/plans-policies/initiative-programs/home-sharing-ordinance": (
        "Los Angeles Home-Sharing Ordinance (CF 14-1635-S2). "
        "Short-term rentals are permitted only in the host's primary residence, defined as "
        "the home where the host lives for at least 6 months per year. Registration is required. "
        "Non-primary residences and investment properties are completely ineligible for STR permits."
    ),
    "https://www.denvergov.org/Government/Agencies/Business-Licensing/Short-Term-Rentals": (
        "Denver Municipal Code Chapter 33. "
        "Denver short-term rental regulations state that an STR license may only be issued "
        "for a primary residence. An applicant must demonstrate they reside at the property "
        "by providing a Colorado driver's license, voter registration, or utility bills."
    ),
    "https://www.sandiego.gov/treasurer/short-term-residential-occupancy": (
        "City of San Diego Short-Term Residential Occupancy (STRO) Ordinance. "
        "The ordinance establishes a tier system. Tier 1 (home share part-time) and Tier 2 (home share full-time) "
        "have no caps. Tier 3 (whole home rentals for more than 20 days/year) is capped at 1% of the city's "
        "housing stock (excluding Mission Beach, which is capped at 30%). Permits are allocated via a lottery system."
    ),
    "https://www.steamboatsprings.net/str": (
        "Steamboat Springs Short-Term Rental Licensing & Zoning. "
        "STR permits are regulated by an Overlay Zone map: "
        "- Green Zone: STRs are permitted and unlimited. "
        "- Yellow Zone: STRs are capped at a specific percentage per neighborhood, and new permits are issued via lottery. "
        "- Red Zone: STRs are completely prohibited in these residential neighborhoods."
    ),
    "https://www.austintexas.gov/str": (
        "City of Austin Short-Term Rental Regulation. "
        "Type 1: Owner-occupied single family or duplex units. "
        "Type 2: Non-owner occupied units. Type 2 STRs are strictly capped and restricted to commercial "
        "zoning districts or specific zoning overlays. They are prohibited in standard single-family residential zones."
    ),
    "https://nola.gov/short-term-rentals": (
        "New Orleans City Council Short-Term Rental Regulations. "
        "Residential Short-Term Rental (NSTR) permits require the host to possess a valid homestead exemption "
        "on the property (proving owner occupancy). Furthermore, there is a block-level density cap of 1 STR "
        "per square block. Commercial STRs (CSTR) are permitted in commercial zones subject to conditional use."
    ),
    "https://www.honolulu.gov/dpp/str.html": (
        "City and County of Honolulu Ordinance 25-02 (formerly Bill 41). "
        "Ordinance 25-02 establishes a 90-day minimum stay requirement for all residential zones "
        "on the island of Oahu. Rentals for fewer than 90 days are prohibited except in resort-zoned areas "
        "or for properties holding a grandfathered Nonconforming Use Certificate (NUC)."
    ),
    "https://ecode360.com/zoning-temporary-structures": (
        "Zoning Code Section 12.4: Accessory structures and temporary living spaces. "
        "Temporary or movable structures, including but not limited to Yurts, recreational vehicles (RVs), "
        "travel trailers, and tents, are not permitted to be used as short-term rentals or transient lodging, "
        "even if the property is located in an eligible STR zoning district. Only permanent residential structures "
        "with active utility connections and certificate of occupancy are eligible."
    ),
    "https://www.lasvegasnevada.gov/str": (
        "Las Vegas Short-Term Rental Rules. "
        "Within Las Vegas city limits, STRs are restricted to owner-occupied properties. "
        "In unincorporated Clark County, STRs are allowed but face strict rules: "
        "properties must be at least 1,000 feet apart, the county has set a total cap of 1% of residential units, "
        "and new permits are issued via a lottery. Moratoriums are currently active in some areas."
    ),
    "https://www.gatlinburgtn.gov/departments/finance/business_licenses.php": (
        "Gatlinburg Municipal Zoning Code for Short-Term Rentals. "
        "STRs are allowed in tourist overlay districts, commercial C-2 zones, and residential zones. "
        "Hosts must obtain a Tourist Accommodation Permit and a local business license. "
        "An annual fire safety inspection is required. A combined sales and local gross receipts tax rate "
        "of 9.75% must be collected and paid on all gross rental income."
    ),
    "https://www.brokenbowok.gov/str-licensing": (
        "Broken Bow Municipal Code Chapter 5. "
        "Short-term rentals are allowed and encouraged. All operators must obtain an STR permit "
        "from the city clerk, register for local lodging tax, and ensure properties are compliant "
        "with standard safety rules (smoke alarms, egress, parking limits)."
    )
}
