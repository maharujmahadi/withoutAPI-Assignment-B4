"""Streamlit web app for building vulnerability scoring and retrofit cost estimation."""

from __future__ import annotations

import os

import streamlit as st

from agent import run_building_consultant
from tools import calculate_vulnerability_score, estimate_retrofit_cost


def _load_env():
    # Load environment variables from .env if present.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _format_currency(value: float) -> str:
    return f"{value:,.0f} Tk"


def _run_manual_ui() -> None:
    st.header("Manual Calculator")

    # Zone options with detailed descriptions from research
    zone_options = {
        "Zone 1 (Pleistocene Terrace) - Locations: Mirpur, Tejgaon, Dhanmondi, Cantonment, Old Dhaka (core areas), Ramna, Shahbagh, Lalmatia - Site Class D (Stiff Soil)": "Zone 1",
        "Zone 2 (Holocene Alluvial Valley Fill and Holocene Terrace) - Locations: Mohammadpur, Rampura, Malibagh, Shahjahanpur, Khilgaon, parts of Mirpur (fringes), Keraniganj (near river), Jatrabari (portions) - Site Class D to E (Stiff to Soft Soil transition)": "Zone 2",
        "Zone 3 (Artificial Fill and Holocene Alluvium) - Locations: Basundhara, Purbachal, Uttara (3rd phase), Mohammadpur (low-lying areas), Rampura (eastern parts), Jatrabari (low areas), Demra, Postogola, Jurain, parts of Keraniganj, Badda (portions) - Site Class E (Soft Soil)": "Zone 3",
    }

    col1, col2 = st.columns(2)
    with col1:
        selected_zone_display = st.selectbox("Soil Zone", list(zone_options.keys()), index=1)
        zone = zone_options[selected_zone_display]
        construction_year = st.number_input("Construction Year", min_value=1900, max_value=2040, value=1995)
        soft_story = st.selectbox(
            "Soft Story Condition", ["Open/Piloti ground floor", "Solid ground floor"], index=0
        )
        structure_type = st.selectbox(
            "Structure Type",
            [
                "URM (Old Dhaka)",
                "RC Soft Story (6-9 story)",
                "RC Infilled (Engineered)",
                "RC Non-Engineered (Poor Detailing)",
                "High-Rise (Deep Pile)",
            ],
        )

    with col2:
        num_floors = st.number_input("Number of Floors", min_value=1, max_value=20, value=1)

        # Dynamic intervention options based on selected zone (from Excel Cost Table)
        intervention_options = {
            "Zone 1": [
                "Column Jacketing (with footing)",
                "Shear Walls (with footing)",
                "Steel bracing work in-fill steel brace",
            ],
            "Zone 2": [
                "Column Jacketing (with footing)",
                "Shear Walls (with footing)",
                "Steel bracing work in-fill steel brace",
                "Deep foundation retrofitting",
            ],
            "Zone 3": [
                "Shear Walls (with footing)",
                "Deep foundation piles",
                "Soil stabilization",
            ],
        }
        intervention = st.selectbox(
            "Retrofit Intervention",
            intervention_options.get(zone, ["Shear Walls (with footing)"],),
        )

        unit_labels = {
            "Column Jacketing (with footing)": "meters of column",
            "Shear Walls (with footing)": "sqm of shear wall",
            "Steel bracing work in-fill steel brace": "sqm of frame",
            "Deep foundation retrofitting": "(consult engineer)",
            "Deep foundation piles": "(consult engineer)",
            "Soil stabilization": "(consult engineer)",
        }
        unit_label = unit_labels.get(intervention, "unit")

        quantity = st.number_input(
            f"Quantity ({unit_label})",
            min_value=0.0,
            value=100.0 if "sqm" in unit_label or "meters" in unit_label else 0.0,
        )

    if st.button("Compute Vulnerability + Cost"):
        vuln = calculate_vulnerability_score(zone, int(construction_year), soft_story, structure_type)
        cost = estimate_retrofit_cost(intervention, float(quantity), zone=zone, num_floors=int(num_floors))

        st.subheader("Vulnerability Score")
        st.write(
            f"**Risk Tier:** {vuln.risk_tier} "
            f"**Total Score:** {vuln.total_score}"  # noqa: E501
            f"(Zone: {vuln.zone_points} pts, Year: {vuln.year_points} pts, Soft story: {vuln.soft_story_points} pts, Structure: {vuln.structure_points} pts)"
        )

        st.subheader("Retrofit Cost Estimate")
        st.write(f"**Intervention:** {cost.intervention_type}")
        st.write(f"**Quantity:** {cost.quantity:,.1f} {cost.unit}")
        st.write(f"**Estimated cost:** {_format_currency(cost.estimated_cost_tk)}")
        st.write("**Cost details:**")
        st.write(cost.details)

    st.warning(
        "Disclaimer: This tool utilizes Artificial Intelligence (AI) to generate responses and risk assessments based on the provided simulation scenarios. AI can occasionally produce incorrect or unverified information. The results should be used for educational and awareness purposes only and do not constitute professional engineering or legal advice. Always consult with a qualified structural engineer for specific building safety assessments."
    )


def _run_agent_ui() -> None:
    st.header("Agent-based Consultant")
    st.write(
        "Describe your building (e.g., 'I have a 5-story building in Mirpur built in 1995 with open ground floor parking'). "
        "The agent will extract parameters, compute a vulnerability score, and provide a retrofit cost estimate."
    )
    user_prompt = st.text_area("Building description", height=150)

    if st.button("Run Agent"):
        if not user_prompt.strip():
            st.error("Please describe your building so the agent can work.")
        else:
            with st.spinner("Consulting the agent..."):
                try:
                    report = run_building_consultant(user_prompt)
                    st.markdown(report)
                except Exception as e:
                    st.error(f"Agent failed: {e}")

    st.warning(
        "Disclaimer: This tool utilizes Artificial Intelligence (AI) to generate responses and risk assessments based on the provided simulation scenarios. AI can occasionally produce incorrect or unverified information. The results should be used for educational and awareness purposes only and do not constitute professional engineering or legal advice. Always consult with a qualified structural engineer for specific building safety assessments."
    )


def main() -> None:
    _load_env()

    st.set_page_config(
        page_title="Dhaka Building Retrofit Consultant",
        page_icon="🏗️",
        layout="wide",
    )

    st.title("Dhaka Building Retrofit Consultant")
    st.write(
        "This tool uses deterministic scoring (based on the provided research tables) and an LLM agent "
        "to recommend retrofit methods and cost estimates."
    )

    mode = st.sidebar.radio("Mode", ["Manual Calculator", "Agent Chat"])

    if mode == "Manual Calculator":
        _run_manual_ui()
    else:
        _run_agent_ui()


if __name__ == "__main__":
    main()
