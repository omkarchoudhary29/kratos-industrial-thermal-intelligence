"""backend/services/compliance_screening.py
----------------------------------------
KRATOS V3 Phase 2 Final Hardening — Regulatory & Environmental Compliance Screening Engine.

Encodes statutory Indian CPCB / SPCB / MoEFCC standards with strict primary gazette provenance:
  - Thermal Power Stations (MoEFCC Notification S.O. 3305(E) Dec 7, 2015 amended by S.O. 1244(E) Mar 31, 2021)
  - Petroleum Refineries & Flare Systems (MoEFCC Notification G.S.R. 186(E) Mar 18, 2008 & CPCB COINDS/18/1983-84)
  - Integrated Iron & Steel Plants (MoEFCC Notification G.S.R. 277(E) Mar 31, 2012)
  - Coal Mining & Handling Yards (Coal Mines Regulations 2017 Reg 133/134 & CPCB Mining Guidelines 2018)
  - Forest Reserves & Eco-Sensitive Zones (Wildlife Protection Act 1972 & MoEFCC ESZ Guidelines Feb 9, 2011)

Screening Tiers (Cautious & Legally Defensible):
  - POTENTIAL_COMPLIANCE_CONCERN: Significant thermal excursion in verified industrial boundary requiring priority review.
  - FURTHER_EVIDENCE_REQUIRED: Elevated heat or ambiguous perimeter requiring ground CEMS/site telemetry.
  - NO_CONCERN_IDENTIFIED: Steady emission within normal historical baseline.
  - INSUFFICIENT_DATA: Sparse observation or unmapped infrastructure.

MANDATORY STATUTORY NOTICE: Satellite thermal observations measure radiated heat flux (MW), NOT stack
concentrations (mg/Nm3) or judicial proof of violation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("compliance_screening")

MANDATORY_LEGAL_DISCLAIMER = (
    "STATUTORY NOTICE & SCIENTIFIC INTEGRITY DISCLAIMER: Satellite thermal remote-sensing observations "
    "are indicative screening tools designed for operational triage, infrastructure awareness, and early prioritization. "
    "Satellite Fire Radiative Power (FRP) measures radiative energy dissipation (in Megawatts), NOT stack particulate "
    "matter (mg/Nm3) or gaseous pollutant concentrations. Satellite detections do NOT constitute legal, regulatory, or judicial "
    "proof of statutory non-compliance under the Environment (Protection) Act, 1986, Air (Prevention and Control of Pollution) "
    "Act, 1981, or Water Act, 1974. Confirmatory compliance enforcement requires physical site inspection, stack sampling by "
    "an accredited laboratory, continuous emission monitoring systems (CEMS) telemetry validation, and formal verification "
    "by competent Central (CPCB) or State Pollution Control Board (SPCB) authorities."
)

REGULATORY_STANDARDS_CATALOG = [
    {
        "id": "cpcb_thermal_power",
        "sector": "Thermal Power Station",
        "statutory_source": "Environment (Protection) Rules, 1986, Schedule I",
        "gazette_notification": "MoEFCC Notification S.O. 3305(E) (Dec 7, 2015) amended by S.O. 1244(E) (Mar 31, 2021)",
        "notification_date": "2015-12-07 / 2021-03-31",
        "regulatory_authority": "Central Pollution Control Board (CPCB) / State PCB / CEA",
        "verification_status": "VERIFIED_ACTIVE",
        "key_limits": {
            "particulate_matter": "<= 30 mg/Nm3 (units installed post-Dec 2016) / <= 50 mg/Nm3 (older units)",
            "sulfur_dioxide_so2": "<= 100 mg/Nm3 (units >= 500 MW)",
            "nitrogen_oxides_nox": "<= 100 mg/Nm3",
            "cooling_water_temp": "<= 5 deg C above ambient receiving water body",
        },
        "thermal_surveillance_relevance": (
            "Anomalous thermal signatures above boiler exhaust or cooling channels indicate potential "
            "flue-gas heat recovery bypass, precipitator offline events, or unthrottled peak dispatch heat release."
        ),
        "stack_concentration_notice": (
            "NOTICE: Satellite FRP measures thermal radiative power (MW), NOT stack PM or SO2 concentration (mg/Nm3). "
            "Excursions indicate abnormal process heat, not direct stack exceedance without CEMS verification."
        ),
        "monitoring_protocol": "Continuous Emission Monitoring System (CEMS) + VIIRS Nighttime Thermal Imaging",
    },
    {
        "id": "cpcb_refinery_flaring",
        "sector": "Petroleum & Chemical Refinery",
        "statutory_source": "MoEFCC Environment (Protection) Second Amendment Rules, 2008 & Petroleum Rules, 2002",
        "gazette_notification": "MoEFCC Notification G.S.R. 186(E) (Mar 18, 2008) & CPCB COINDS/18/1983-84",
        "notification_date": "2008-03-18",
        "regulatory_authority": "CPCB / Petroleum & Explosives Safety Organization (PESO) / SPCB",
        "verification_status": "VERIFIED_ACTIVE",
        "key_limits": {
            "routine_flaring": "Prohibited during normal operations except pilot and safety purge",
            "combustion_efficiency": ">= 98% destruction efficiency for volatile organic compounds",
            "flare_gas_recovery": "Mandatory Flare Gas Recovery System (FGRS) installation",
            "so2_emissions_sr_unit": "<= 10 kg/tonne of crude processed",
        },
        "thermal_surveillance_relevance": (
            "Prolonged or massive FRP spikes at refinery flare tips indicate emergency blowdown events, "
            "upset process conditions in fluid catalytic cracking (FCC) units, or incomplete combustion releases."
        ),
        "stack_concentration_notice": (
            "NOTICE: Satellite FRP captures flare heat dissipation in MW. Flare gas recovery compliance requires "
            "ultrasonic flare gas flowmeters and optical gas imaging (OGI) on-site."
        ),
        "monitoring_protocol": "Optical Gas Imaging (OGI) + VIIRS Continuous Mid-IR Surveillance",
    },
    {
        "id": "cpcb_steel_metallurgy",
        "sector": "Steel & Metallurgy Plant",
        "statutory_source": "Environment (Protection) Rules, 1986, Schedule I (Standards for Integrated Iron & Steel Plants)",
        "gazette_notification": "MoEFCC Notification G.S.R. 277(E) (Mar 31, 2012)",
        "notification_date": "2012-03-31",
        "regulatory_authority": "CPCB / Ministry of Steel / State PCB",
        "verification_status": "VERIFIED_ACTIVE",
        "key_limits": {
            "blast_furnace_stack": "<= 50 mg/Nm3 particulate matter",
            "coke_oven_plushing": "<= 5 seconds per push emission duration",
            "fugitive_taphole_emissions": "Secondary capture ventilation with baghouse filtration mandatory",
            "carbon_monoxide_recovery": "Mandatory recovery of Basic Oxygen Furnace (BOF) gas",
        },
        "thermal_surveillance_relevance": (
            "Excessive external thermal radiative power can signify slag yard open-air dumping excursions, "
            "torpedo ladle insulation degradation, or uncontained secondary ladle furnace flares."
        ),
        "stack_concentration_notice": (
            "NOTICE: Satellite FRP indicates radiant surface heat. Blast furnace particulate emission limits "
            "must be verified via isokinetic stack sampling."
        ),
        "monitoring_protocol": "Boundary Air Monitoring + High-Resolution Thermal Radiometry",
    },
    {
        "id": "cpcb_coal_mining",
        "sector": "Coal Mine & Handling Yard",
        "statutory_source": "Mines Act, 1952 & Coal Mines Regulations, 2017 (Reg 133/134: Precaution against Spontaneous Heating)",
        "gazette_notification": "DGMS Circulars on Spontaneous Combustion & CPCB Comprehensive Guidelines for Coal Mining (2018)",
        "notification_date": "2017-11-27",
        "regulatory_authority": "Directorate General of Mines Safety (DGMS) / Coal Controller / SPCB",
        "verification_status": "VERIFIED_ACTIVE",
        "key_limits": {
            "stockpile_residence_time": "<= 30 days without compaction for high-volatile coals",
            "thermal_monitoring": "Weekly infrared thermographic inspection of active stock benches",
            "fire_fighting_water": "Dedicated water mist cannons and blanketing soil cover mandatory",
            "ambient_pm10": "<= 100 ug/m3 in core mining zone",
        },
        "thermal_surveillance_relevance": (
            "Subsurface coal seam fires and stockpile auto-ignition generate persistent, low-intensity "
            "diffuse thermal anomalies that can smolder undetected before escalating into surface blazes."
        ),
        "stack_concentration_notice": (
            "NOTICE: Diffuse thermal signatures indicate surface temperature anomalies; DGMS compliance "
            "requires in-situ thermal probing and carbon monoxide gas chromatography."
        ),
        "monitoring_protocol": "Drone/Satellite Thermography + In-situ Core Temperature Probing",
    },
    {
        "id": "moefcc_forest_esz",
        "sector": "Forest Landscape & Canopy",
        "statutory_source": "Wildlife (Protection) Act, 1972 & Forest (Conservation) Act, 1980 / ESZ Framework",
        "gazette_notification": "Guidelines for Declaration of Eco-Sensitive Zones around National Parks & Sanctuaries (Feb 9, 2011)",
        "notification_date": "2011-02-09",
        "regulatory_authority": "State Forest Department / National Board for Wildlife (NBWL)",
        "verification_status": "VERIFIED_ACTIVE",
        "key_limits": {
            "commercial_incineration": "Strictly prohibited within declared Eco-Sensitive Zones (default interim 10 km radius where site notification pending)",
            "fire_season_readiness": "Mandatory fireline maintenance and fire-watch towers during dry seasons",
            "stubble_burning": "Prohibited under National Green Tribunal (NGT) Principal Bench orders",
        },
        "thermal_surveillance_relevance": (
            "Any thermal hotspot inside declared wildlife sanctuaries or reserve forest boundaries "
            "triggers immediate forest fire rapid response protocols."
        ),
        "stack_concentration_notice": (
            "NOTICE: Active forest fire detections trigger ecological alert response, not industrial stack audits."
        ),
        "monitoring_protocol": "FSI Van Agni Forest Fire Portal + VIIRS Active Fire Feed",
    },
]


class ComplianceScreeningEngine:
    def __init__(self):
        self.standards = REGULATORY_STANDARDS_CATALOG
        self.disclaimer = MANDATORY_LEGAL_DISCLAIMER

    def get_standards_catalog(self) -> List[Dict[str, Any]]:
        return self.standards

    def match_sector_standard(self, facility_category: str) -> Optional[Dict[str, Any]]:
        cat_lower = str(facility_category or "").lower()
        if any(k in cat_lower for k in ["power", "thermal_power", "generator"]):
            return self.standards[0]
        if any(k in cat_lower for k in ["refinery", "petro", "oil", "gas", "flare"]):
            return self.standards[1]
        if any(k in cat_lower for k in ["steel", "iron", "blast", "smelter", "industrial", "manufacturing"]):
            return self.standards[2]
        if any(k in cat_lower for k in ["mine", "quarry", "colliery", "coal"]):
            return self.standards[3]
        if any(k in cat_lower for k in ["forest", "canopy", "wildlife", "tree"]):
            return self.standards[4]
        return None

    def screen_facility_compliance(
        self,
        facility_name: str,
        facility_category: str,
        max_frp_ratio: float = 1.0,
        max_frp_mw: float = 0.0,
        distance_m: Optional[float] = None,
        detection_count: int = 1,
        is_anomaly_flagged: bool = False,
    ) -> Dict[str, Any]:
        """Perform cautious, defensible regulatory compliance screening."""
        matched_standard = self.match_sector_standard(facility_category)

        # Baseline checks
        if not matched_standard:
            return {
                "facility_name": facility_name or "Unidentified Facility",
                "facility_category": facility_category,
                "applicable_standard": None,
                "screening_status": "INSUFFICIENT_DATA",
                "screening_label": "No Sector Standard Mapped",
                "screening_rationale": "Facility category does not map to registered CPCB / MoEFCC industrial point-source standards.",
                "action_recommended": "Geospatial cadastral mapping to confirm operational category.",
                "legal_disclaimer": self.disclaimer,
            "disclaimer": self.disclaimer,
            }

        # Check proximity
        is_proximate = distance_m is not None and distance_m <= 1000.0

        if not is_proximate:
            return {
                "facility_name": facility_name or "Unidentified Facility",
                "facility_category": facility_category,
                "applicable_standard": matched_standard,
                "screening_status": "FURTHER_EVIDENCE_REQUIRED",
                "screening_label": "Peripheral Distance Exceedance",
                "screening_rationale": (
                    f"Thermal observation is located {distance_m:.0f} m from mapped facility boundary. "
                    "Spatial association is unconfirmed; localized ground reconnaissance recommended."
                ) if distance_m else "Thermal source lacks confirmed spatial proximity to facility polygon.",
                "action_recommended": "Drone boundary survey or cadastral parcel verification.",
                "legal_disclaimer": self.disclaimer,
            "disclaimer": self.disclaimer,
            }

        # Assess thermal exceedance
        if max_frp_ratio >= 3.5 or (max_frp_mw >= 80.0 and is_anomaly_flagged):
            screening_status = "POTENTIAL_COMPLIANCE_CONCERN"
            screening_label = "Elevated Operational Thermal Exceedance"
            screening_rationale = (
                f"Sustained thermal signature ({max_frp_mw:.1f} MW, {max_frp_ratio:.1f}x baseline) within mapped "
                f"{matched_standard['sector']} perimeter. Exceeds historical operational envelope. Warranted for priority review."
            )
            action_recommended = "Cross-reference with facility Continuous Emission Monitoring Systems (CEMS) and notify State PCB regional officer."
        elif max_frp_ratio >= 2.0 or is_anomaly_flagged:
            screening_status = "FURTHER_EVIDENCE_REQUIRED"
            screening_label = "Moderate Baseline Departure"
            screening_rationale = (
                f"Thermal output is {max_frp_ratio:.1f}x historical baseline. May represent scheduled process turnaround, "
                "temporary flaring, or sensor edge distortion. Ground telemetry verification advised."
            )
            action_recommended = "Monitor next orbital overpass and request facility process log."
        else:
            screening_status = "NO_CONCERN_IDENTIFIED"
            screening_label = "Normal Operational Range"
            screening_rationale = (
                f"Thermal observations ({max_frp_mw:.1f} MW, {max_frp_ratio:.1f}x baseline) remain consistent with "
                f"registered {matched_standard['sector']} historical operating limits."
            )
            action_recommended = "Routine automated surveillance; no manual escalation required."

        return {
            "facility_name": facility_name or "Unidentified Facility",
            "facility_category": facility_category,
            "applicable_standard": matched_standard,
            "screening_status": screening_status,
            "screening_label": screening_label,
            "screening_rationale": screening_rationale,
            "action_recommended": action_recommended,
            "distance_m": distance_m,
            "detection_count": detection_count,
            "legal_disclaimer": self.disclaimer,
            "disclaimer": self.disclaimer,
        }


compliance_screening_engine = ComplianceScreeningEngine()
