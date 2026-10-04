#!/usr/bin/env python3
"""
Database Seeder for National Weather Platform.
Generates 200+ realistic sample weather events across Indian states.
"""

import asyncio
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.abspath(__file__)) + "/../backend")

from app.core.database import async_session_factory, engine, Base
from app.models.weather_event import (
    WeatherEvent, EventType, SeverityLevel, EventSource, VerificationStatus
)
from app.models.user import User, UserRole
from app.core.database import get_db

from app.ml.fake_detector import FakeDetector
from app.ml.categorizer import Categorizer
from app.utils.geolocation import get_city_coordinates, INDIAN_CITY_COORDINATES, INDIAN_STATE_CENTERS

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

FAKE_DETECTOR = FakeDetector()
CATEGORIZER = Categorizer()

EVENT_TEMPLATES = {
    "rainfall": {
        "titles": [
            "Heavy rainfall in {city}, waterlogging reported in multiple areas",
            "IMD predicts intense rainfall over {city} for next 48 hours",
            "Continuous rainfall disrupts daily life in {city}",
            "Record rainfall of {amount}mm recorded in {city} in 24 hours",
            "Low-lying areas of {city} submerged after heavy downpour",
            "Monsoon rainfall arrives early in {city}, sets new records",
            "Flash flood warning issued for {city} due to heavy rainfall",
            "Water supply severely affected in {city} after heavy rains",
            "Airport operations disrupted due to heavy rainfall in {city}",
            "Rail services halted as tracks submerged in {city}",
        ],
        "descriptions": [
            "Heavy rainfall lashed {city} today, causing severe waterlogging in several areas. The India Meteorological Department recorded {amount}mm of rainfall in the past 24 hours. Traffic was disrupted on major roads and rescue teams were deployed in affected areas. Residents in low-lying areas were advised to move to safer locations.",
            "The India Meteorological Department has issued a red alert for {city} predicting heavy to very heavy rainfall over the next 48 hours. Citizens are advised to stay indoors and avoid unnecessary travel. District administration has set up relief camps in vulnerable areas.",
            "Continuous rainfall since morning has brought life to a standstill in {city}. Several roads are waterlogged and schools have been closed as a precautionary measure. The local meteorological office has recorded {amount}mm of rainfall.",
        ],
    },
    "thunderstorm": {
        "titles": [
            "Severe thunderstorm with gusty winds hits {city}",
            "Lightning strikes damage property in {city}",
            "Thunderstorm warning issued for {city} and surrounding areas",
            "Heavy thunderstorm brings relief from heat in {city}",
            "Multiple lightning incidents reported in {city} district",
            "Thunderstorm with hail disrupts evening activities in {city}",
            "Strong thunderstorm uproots trees in {city}",
            " IMD forecasts thunderstorm activity across {city} region",
        ],
        "descriptions": [
            "A severe thunderstorm accompanied by gusty winds of 70 km/h hit {city} this evening, uprooting several trees and damaging property. Lightning strikes were reported in multiple areas, though no casualties were reported. The India Meteorological Department had issued a warning earlier in the day.",
            "Thunderstorm activity was observed across {city} and surrounding districts today. Hail was reported in several areas, causing damage to standing crops. The local administration has assessed the damage and is providing relief to affected farmers.",
        ],
    },
    "flooding": {
        "titles": [
            "Flash floods in {city}, rescue operations underway",
            "River water level rises above danger mark near {city}",
            "Flood situation worsens in {city} as more areas affected",
            "Over {affected} people evacuated from flood-affected areas near {city}",
            "Bridges damaged as floodwaters surge through {city} district",
            "Flood relief camps set up across {city} as waters rise",
            "Agricultural land submerged due to flooding near {city}",
            "Dam releases water affecting downstream areas near {city}",
        ],
        "descriptions": [
            "Flash floods triggered by heavy rainfall have inundated several areas in and around {city}. Over {affected} people have been evacuated to relief camps set up by the district administration. NDRF and SDRF teams are conducting rescue operations using boats. The river flowing through {city} has crossed the danger mark and continues to rise.",
            "The flood situation in {city} has worsened with more areas getting affected. Multiple bridges and roads have been damaged, cutting off connectivity to several villages. The state government has sought additional NDRF teams and the Indian Army has been put on standby.",
        ],
    },
    "heatwave": {
        "titles": [
            "Heatwave conditions in {city}, temperature crosses {temp}°C",
            "Extreme heatwave grips {city} for the fifth consecutive day",
            "Heatstroke cases reported in {city} as temperatures soar",
            "Water scarcity reported in rural areas near {city} during heatwave",
            "Heatwave warning issued for {city} and surrounding districts",
            "Night temperatures remain above 30°C in {city}",
            "Heatwave conditions expected to persist in {city} this week",
            "Cooling centers opened in {city} to help residents cope with heat",
        ],
        "descriptions": [
            "Severe heatwave conditions continue to grip {city} with the maximum temperature crossing {temp}°C today. The India Meteorological Department has issued a heatwave warning for the region. Several cases of heatstroke have been reported at local hospitals. Authorities have opened cooling centers and are distributing water in affected areas.",
            "The ongoing heatwave in {city} has entered its fifth day with no respite in sight. Temperatures have remained above {temp}°C for several days. The district administration has declared a heatwave emergency and directed schools to adjust their timings.",
        ],
    },
    "fog": {
        "titles": [
            "Dense fog disrupts transportation in {city}",
            "Visibility drops below 50 meters at {city} airport",
            "Fog advisory issued for {city} as morning visibility remains poor",
            "Multiple accidents reported due to dense fog near {city}",
            "Flight operations disrupted at {city} due to dense fog",
            "Rail services delayed as dense fog engulfs {city}",
            "Cold day conditions persist in {city} with dense morning fog",
            "Dense fog blankets {city}, road and rail traffic affected",
        ],
        "descriptions": [
            "Dense fog engulfed {city} this morning, reducing visibility to less than 50 meters at several locations. Flight operations at the local airport were severely affected with multiple flights delayed and some diverted. Road and rail traffic was also disrupted. The IMD has predicted foggy conditions to continue for the next few days.",
        ],
    },
    "dust_storm": {
        "titles": [
            "Dust storm sweeps through {city}, reducing visibility",
            "Massive dust storm hits {city}, damages property",
            "Dust storm disrupts power supply in {city}",
            "Strong winds carry dust reducing visibility across {city}",
            "Dust storm warning for {city} and surrounding areas",
        ],
        "descriptions": [
            "A massive dust storm swept through {city} this evening, reducing visibility dramatically and disrupting power supply across several areas. Trees were uprooted and temporary structures were damaged. The India Meteorological Department had issued a dust storm warning for the region.",
        ],
    },
    "strong_winds": {
        "titles": [
            "Strong winds of {wind_speed} km/h batter {city}",
            "Windstorm damages rooftops and signboards in {city}",
            "Gusty winds disrupt outdoor events in {city}",
            "Strong winds cause flight delays at {city} airport",
            "Wind advisory issued for {city} as gusts intensify",
            "Strong westerly winds affecting {city} region",
        ],
        "descriptions": [
            "Strong winds of up to {wind_speed} km/h battered {city} today, damaging rooftops, uprooting trees, and blowing away signboards. Several flights at the local airport were delayed due to crosswinds. The IMD has issued a wind advisory for the region predicting continued gusty conditions.",
        ],
    },
    "cyclone": {
        "titles": [
            "Cyclone approaching {city} coast, evacuations ordered",
            "Severe cyclonic storm likely to make landfall near {city}",
            "Cyclone warning: NDRF teams deployed near {city}",
            "Deep depression in Bay of Bengal may intensify into cyclone near {city}",
            "Cyclone alert for coastal areas near {city}",
        ],
        "descriptions": [
            "A deep depression in the Bay of Bengal has intensified into a severe cyclonic storm and is expected to make landfall near {city} within the next 24 hours. The India Meteorological Department has issued a cyclone warning for coastal areas. NDRF teams have been deployed and evacuation of low-lying areas is underway. The Indian Navy has been put on standby for relief operations.",
        ],
    },
}

VERIFICATION_WEIGHTS = [
    (VerificationStatus.VERIFIED, 0.35),
    (VerificationStatus.PENDING, 0.35),
    (VerificationStatus.NEEDS_REVIEW, 0.15),
    (VerificationStatus.REJECTED, 0.15),
]


def weighted_choice(choices):
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    cumulative = 0
    for choice, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return choice
    return choices[-1][0]


def random_date(start_days=90, end_days=0):
    now = datetime.utcnow()
    start = now - timedelta(days=start_days)
    end = now - timedelta(days=end_days)
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


async def seed_database():
    logger = __import__('logging').getLogger("seed_database")

    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        logger.info("Creating admin user...")
        admin = User(
            username="admin",
            email="admin@weatherplatform.gov.in",
            hashed_password=pwd_context.hash("admin123"),
            full_name="Platform Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        analyst = User(
            username="analyst",
            email="analyst@weatherplatform.gov.in",
            hashed_password=pwd_context.hash("analyst123"),
            full_name="Weather Analyst",
            role=UserRole.ANALYST,
            is_active=True,
        )
        citizen1 = User(
            username="citizen1",
            email="citizen1@example.com",
            hashed_password=pwd_context.hash("citizen123"),
            full_name="Rajesh Kumar",
            role=UserRole.CITIZEN,
            is_active=True,
        )
        citizen2 = User(
            username="citizen2",
            email="citizen2@example.com",
            hashed_password=pwd_context.hash("citizen123"),
            full_name="Priya Sharma",
            role=UserRole.CITIZEN,
            is_active=True,
        )
        db.add_all([admin, analyst, citizen1, citizen2])
        await db.flush()
        logger.info("Created 4 users (admin, analyst, 2 citizens)")

        users = [admin, analyst, citizen1, citizen2]

        sources = [EventSource.TWITTER, EventSource.WEB, EventSource.API, EventSource.CITIZEN_REPORT]
        source_weights = [0.25, 0.25, 0.25, 0.25]

        logger.info("Generating weather events...")
        events = []

        cities_pool = list(INDIAN_CITY_COORDINATES.keys())
        state_cities = {}
        for city, state in [
            ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Nagpur", "Maharashtra"),
            ("Delhi", "Delhi"), ("New Delhi", "Delhi"),
            ("Bengaluru", "Karnataka"), ("Mysuru", "Karnataka"),
            ("Chennai", "Tamil Nadu"), ("Coimbatore", "Tamil Nadu"), ("Madurai", "Tamil Nadu"),
            ("Kolkata", "West Bengal"), ("Siliguri", "West Bengal"),
            ("Hyderabad", "Telangana"), ("Warangal", "Telangana"),
            ("Ahmedabad", "Gujarat"), ("Surat", "Gujarat"), ("Rajkot", "Gujarat"),
            ("Jaipur", "Rajasthan"), ("Jodhpur", "Rajasthan"),
            ("Lucknow", "Uttar Pradesh"), ("Varanasi", "Uttar Pradesh"), ("Kanpur", "Uttar Pradesh"),
            ("Bhopal", "Madhya Pradesh"), ("Indore", "Madhya Pradesh"),
            ("Patna", "Bihar"),
            ("Ranchi", "Jharkhand"), ("Dhanbad", "Jharkhand"),
            ("Bhubaneswar", "Odisha"), ("Cuttack", "Odisha"),
            ("Kochi", "Kerala"), ("Thiruvananthapuram", "Kerala"),
            ("Chandigarh", "Chandigarh"),
            ("Guwahati", "Assam"),
            ("Shimla", "Himachal Pradesh"),
            ("Dehradun", "Uttarakhand"),
            ("Srinagar", "Jammu and Kashmir"),
            ("Amritsar", "Punjab"),
            ("Ludhiana", "Punjab"),
            ("Imphal", "Manipur"),
            ("Shillong", "Meghalaya"),
            ("Agartala", "Tripura"),
            ("Aizawl", "Mizoram"),
            ("Kohima", "Nagaland"),
            ("Gangtok", "Sikkim"),
            ("Panaji", "Goa"),
            ("Raipur", "Chhattisgarh"),
            ("Visakhapatnam", "Andhra Pradesh"),
            ("Tirupati", "Andhra Pradesh"),
        ]:
            state_cities[city] = state

        event_type_list = list(EventType)

        for i in range(250):
            event_type = random.choice(event_type_list)
            templates = EVENT_TEMPLATES.get(event_type.value, EVENT_TEMPLATES["rainfall"])

            city = random.choice(list(state_cities.keys()))
            state = state_cities[city]
            coords = get_city_coordinates(city)

            amount = random.randint(50, 350)
            temp = random.randint(41, 50)
            wind_speed = random.randint(60, 120)
            affected = random.randint(500, 50000)

            title_template = random.choice(templates["titles"])
            title = title_template.format(
                city=city, state=state, amount=amount, temp=temp,
                wind_speed=wind_speed, affected=affected
            )

            desc_template = random.choice(templates["descriptions"])
            description = desc_template.format(
                city=city, state=state, amount=amount, temp=temp,
                wind_speed=wind_speed, affected=affected
            )

            source = random.choices(sources, weights=source_weights, k=1)[0]
            severity = random.choice(list(SeverityLevel))
            verification_status = weighted_choice(VERIFICATION_WEIGHTS)

            is_fake = random.random() < 0.08
            fake_confidence = random.uniform(0.6, 0.95) if is_fake else random.uniform(0.05, 0.3)

            reporter = random.choice(users)
            reporter_id = reporter.id if random.random() > 0.3 else None
            verifier_id = admin.id if verification_status != VerificationStatus.PENDING else None

            reported_at = random_date(start_days=90, end_days=1)
            created_at = reported_at + timedelta(seconds=random.randint(0, 60))

            event = WeatherEvent(
                title=title,
                description=description,
                event_type=event_type,
                severity=severity,
                source=source,
                source_url=f"https://example.com/weather/event/{i+1}" if random.random() > 0.3 else None,
                source_id=f"src_{random.randint(100000, 999999)}" if source in (EventSource.TWITTER, EventSource.CITIZEN_REPORT) else None,
                city=city,
                state=state,
                latitude=coords.get("latitude", 28.6139) + random.uniform(-0.1, 0.1) if coords.get("latitude") else 28.6139,
                longitude=coords.get("longitude", 77.2090) + random.uniform(-0.1, 0.1) if coords.get("longitude") else 77.2090,
                photos=[],
                videos=[],
                metadata_={"source": source.value, "city": city, "state": state},
                verification_status=verification_status,
                is_fake=is_fake,
                fake_confidence=round(fake_confidence, 3),
                category_confidence=round(random.uniform(0.5, 0.99), 3),
                reported_by_id=reporter_id,
                verified_by_id=verifier_id,
                created_at=created_at,
                updated_at=created_at,
                reported_at=reported_at,
            )
            events.append(event)

        db.add_all(events)
        await db.commit()

        logger.info(f"Seeded {len(events)} weather events")
        logger.info(f"Event type distribution:")

        type_counts = {}
        for e in events:
            type_counts[e.event_type.value] = type_counts.get(e.event_type.value, 0) + 1
        for t, c in sorted(type_counts.items()):
            logger.info(f"  {t}: {c}")

        logger.info(f"State distribution (top 10):")
        state_counts = {}
        for e in events:
            if e.state:
                state_counts[e.state] = state_counts.get(e.state, 0) + 1
        for s, c in sorted(state_counts.items(), key=lambda x: -x[1])[:10]:
            logger.info(f"  {s}: {c}")

        logger.info(f"Verification status distribution:")
        ver_counts = {}
        for e in events:
            ver_counts[e.verification_status.value] = ver_counts.get(e.verification_status.value, 0) + 1
        for v, c in sorted(ver_counts.items()):
            logger.info(f"  {v}: {c}")

        logger.info(f"Fake events: {sum(1 for e in events if e.is_fake)}")
        logger.info("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
