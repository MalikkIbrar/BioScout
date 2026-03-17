"""
Management command to seed BioScout with 20 realistic Pakistan wildlife observations.

Usage:
    python manage.py seed_data
    python manage.py seed_data --no-delete   # keep existing data
"""

import random
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from observations.models import Observation

SPECIES_DATA = [
    {
        "species_name": "House Sparrow",
        "category": "bird",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "city": "Lahore",
        "notes": (
            "House Sparrow (Passer domesticus) is one of the most widespread birds in "
            "Pakistan. Highly adaptable to urban environments, it nests in building "
            "crevices and feeds on grains and insects. Common year-round in Lahore."
        ),
    },
    {
        "species_name": "Common Myna",
        "category": "bird",
        "latitude": 24.8607,
        "longitude": 67.0011,
        "city": "Karachi",
        "notes": (
            "Common Myna (Acridotheres tristis) is a highly intelligent, vocal bird "
            "found throughout Pakistan. It thrives in urban areas and is known for "
            "mimicking sounds. Listed as one of the world's 100 worst invasive species."
        ),
    },
    {
        "species_name": "Rose-ringed Parakeet",
        "category": "bird",
        "latitude": 33.7215,
        "longitude": 73.0433,
        "city": "Islamabad",
        "notes": (
            "Rose-ringed Parakeet (Psittacula krameri) forms large, noisy flocks in "
            "Islamabad's residential areas. Bright green plumage with a distinctive "
            "pink and black neck ring on males. Feeds on fruits, seeds, and flowers."
        ),
    },
    {
        "species_name": "Hoopoe",
        "category": "bird",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "city": "Peshawar",
        "notes": (
            "Hoopoe (Upupa epops) is a striking bird with a distinctive crown of "
            "feathers and a long curved bill. Common in Peshawar's gardens and "
            "orchards. Feeds on insects and larvae found in soil. National bird of Israel."
        ),
    },
    {
        "species_name": "Black Kite",
        "category": "bird",
        "latitude": 31.5497,
        "longitude": 74.3436,
        "city": "Lahore",
        "notes": (
            "Black Kite (Milvus migrans) is a medium-sized raptor extremely common "
            "over Pakistani cities. Soars on thermals and scavenges food scraps. "
            "Plays an important ecological role as an urban scavenger in Lahore."
        ),
    },
    {
        "species_name": "Common Peafowl",
        "category": "bird",
        "latitude": 25.8943,
        "longitude": 68.5247,
        "city": "Sindh",
        "notes": (
            "Common Peafowl (Pavo cristatus) is found in the forests and scrublands "
            "of Sindh. The male's iridescent blue-green plumage and elaborate tail "
            "feathers are used in courtship displays. Feeds on seeds, insects, and small reptiles."
        ),
    },
    {
        "species_name": "Snow Leopard",
        "category": "mammal",
        "latitude": 35.9208,
        "longitude": 74.3083,
        "city": "Gilgit-Baltistan",
        "notes": (
            "Snow Leopard (Panthera uncia) is a Vulnerable apex predator of the "
            "Karakoram and Himalayan ranges. Pakistan holds an estimated 200-420 "
            "individuals. Preys on blue sheep and ibex. Threatened by poaching and "
            "habitat loss. Camera trap sighting at 4,200m elevation."
        ),
    },
    {
        "species_name": "Rhesus Macaque",
        "category": "mammal",
        "latitude": 33.9042,
        "longitude": 73.3900,
        "city": "Murree",
        "notes": (
            "Rhesus Macaque (Macaca mulatta) troops are commonly seen along the "
            "Murree hills. Highly social primates that live in groups of 20-200. "
            "Increasingly dependent on tourist food handouts, which disrupts their "
            "natural foraging behaviour."
        ),
    },
    {
        "species_name": "Desert Fox",
        "category": "mammal",
        "latitude": 30.3753,
        "longitude": 69.3451,
        "city": "Punjab",
        "notes": (
            "Desert Fox (Vulpes vulpes pusilla) is a small canid found in the arid "
            "and semi-arid zones of Pakistan. Highly adapted to desert life with large "
            "ears for heat dissipation. Nocturnal hunter of rodents, insects, and small birds."
        ),
    },
    {
        "species_name": "Himalayan Brown Bear",
        "category": "mammal",
        "latitude": 35.2227,
        "longitude": 72.4258,
        "city": "Swat",
        "notes": (
            "Himalayan Brown Bear (Ursus arctos isabellinus) is a Critically Endangered "
            "subspecies found in Swat and Chitral. Fewer than 150 remain in Pakistan. "
            "Omnivorous, feeding on berries, roots, and small mammals. Hibernates in "
            "winter at high altitudes."
        ),
    },
    {
        "species_name": "Spectacled Cobra",
        "category": "reptile",
        "latitude": 25.3960,
        "longitude": 68.3578,
        "city": "Sindh",
        "notes": (
            "Spectacled Cobra (Naja naja) is one of the 'Big Four' venomous snakes "
            "responsible for most snakebite deaths in Pakistan. Named for the spectacle "
            "pattern on its hood. Found in agricultural fields and near human settlements "
            "in Sindh. Plays a vital role in rodent pest control."
        ),
    },
    {
        "species_name": "Monitor Lizard",
        "category": "reptile",
        "latitude": 29.3544,
        "longitude": 66.3597,
        "city": "Balochistan",
        "notes": (
            "Bengal Monitor (Varanus bengalensis) is a large lizard found across "
            "Balochistan's rocky terrain. Can reach 1.75m in length. An opportunistic "
            "carnivore feeding on insects, eggs, small mammals, and carrion. "
            "Illegally hunted for its skin and meat."
        ),
    },
    {
        "species_name": "Star Tortoise",
        "category": "reptile",
        "latitude": 31.4504,
        "longitude": 73.1350,
        "city": "Punjab",
        "notes": (
            "Indian Star Tortoise (Geochelone elegans) has a distinctive star-patterned "
            "shell. Found in dry grasslands and scrub forests of Punjab. Herbivorous, "
            "feeding on grasses and fallen fruit. Vulnerable due to illegal wildlife "
            "trade — heavily collected for the pet trade."
        ),
    },
    {
        "species_name": "Neem Tree",
        "category": "plant",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "city": "Lahore",
        "notes": (
            "Neem (Azadirachta indica) is one of the most important trees in Pakistan, "
            "lining streets across Lahore. Every part of the tree has medicinal uses — "
            "leaves, bark, seeds, and oil. Natural insecticide properties make it "
            "valuable in organic farming. Provides dense shade in summer."
        ),
    },
    {
        "species_name": "Peepal Tree",
        "category": "plant",
        "latitude": 33.7215,
        "longitude": 73.0433,
        "city": "Islamabad",
        "notes": (
            "Peepal (Ficus religiosa) is a sacred fig tree revered in Hindu, Buddhist, "
            "and Jain traditions. Found throughout Islamabad's older neighbourhoods. "
            "Provides habitat for hundreds of bird and insect species. One of the few "
            "trees that releases oxygen at night."
        ),
    },
    {
        "species_name": "Common Jezebel Butterfly",
        "category": "insect",
        "latitude": 24.9056,
        "longitude": 67.0822,
        "city": "Karachi",
        "notes": (
            "Common Jezebel Butterfly (Delias eucharis) is one of the most beautiful "
            "and commonly seen butterflies in Pakistan. Found in gardens and parks "
            "across the country. Brilliant yellow, red, and orange underside. "
            "Caterpillars feed on mistletoe plants."
        ),
    },
    {
        "species_name": "Atlas Moth",
        "category": "insect",
        "latitude": 34.1688,
        "longitude": 73.2215,
        "city": "KPK",
        "notes": (
            "Atlas Moth (Attacus atlas) is one of the largest moths in the world, with "
            "a wingspan up to 25cm. Found in the forested hills of KPK. Adults have no "
            "functional mouth and live only 1-2 weeks, surviving on fat reserves from "
            "the caterpillar stage."
        ),
    },
    {
        "species_name": "Common Tiger Butterfly",
        "category": "insect",
        "latitude": 31.5497,
        "longitude": 74.3436,
        "city": "Lahore",
        "notes": (
            "Common Tiger Butterfly (Danaus genutia) is a widespread species found in "
            "gardens and open areas across Lahore. Its bright orange and black pattern "
            "warns predators of its toxicity, acquired from milkweed plants consumed "
            "as a caterpillar. An important pollinator."
        ),
    },
    {
        "species_name": "Himalayan Marmot",
        "category": "mammal",
        "latitude": 35.8884,
        "longitude": 74.4584,
        "city": "Gilgit",
        "notes": (
            "Himalayan Marmot (Marmota himalayana) is a large ground squirrel found "
            "in alpine meadows above 3,500m in Gilgit-Baltistan. Lives in colonies "
            "and hibernates for 6-7 months. Emits loud alarm whistles when predators "
            "approach. Important prey for Snow Leopards and Golden Eagles."
        ),
    },
    {
        "species_name": "Markhor",
        "category": "mammal",
        "latitude": 36.4200,
        "longitude": 74.8000,
        "city": "Gilgit-Baltistan",
        "notes": (
            "Markhor (Capra falconeri) is the national animal of Pakistan, found in the "
            "rocky mountain terrain of Gilgit-Baltistan, KPK, and AJK. The male's "
            "spectacular corkscrew horns can reach 160cm. Once Endangered, it has "
            "recovered to Near Threatened thanks to community-based conservation."
        ),
    },
    {
        "species_name": "Houbara Bustard",
        "category": "bird",
        "latitude": 28.3000,
        "longitude": 64.5000,
        "city": "Balochistan",
        "notes": (
            "Houbara Bustard (Chlamydotis macqueenii) is an iconic desert bird of "
            "Balochistan and Sindh. Vulnerable species that winters in Pakistan's arid "
            "plains. Traditionally hunted by Arab falconers — a major conservation "
            "controversy. Pakistan hosts critical wintering populations."
        ),
    },
    {
        "species_name": "Indus River Dolphin",
        "category": "mammal",
        "latitude": 27.5000,
        "longitude": 68.7000,
        "city": "Sindh",
        "notes": (
            "Indus River Dolphin (Platanista minor) is found ONLY in Pakistan's Indus "
            "River — one of the world's rarest freshwater dolphins. Endangered with "
            "only ~1,800 individuals remaining. Functionally blind, navigates by "
            "echolocation. Threatened by barrages, fishing nets, and water pollution."
        ),
    },
]


class Command(BaseCommand):
    """Django management command to seed the database with sample observations."""

    help = "Seed the database with 22 realistic Pakistan wildlife observations."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--no-delete",
            action="store_true",
            help="Do not delete existing observations before seeding.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["no_delete"]:
            count, _ = Observation.objects.all().delete()
            self.stdout.write(f"🗑️  Deleted {count} existing observations.")

        now = timezone.now()
        ai_identified_indices = set(random.sample(range(22), 16))

        # Spread dates: 5 in last 7 days, 10 in last 8-30 days, 7 older than 30 days
        date_pool = (
            [random.randint(1, 7) for _ in range(5)]      # last week
            + [random.randint(8, 30) for _ in range(10)]  # last month
            + [random.randint(31, 90) for _ in range(7)]  # older
        )
        random.shuffle(date_pool)

        for idx, data in enumerate(SPECIES_DATA):
            days_ago = date_pool[idx]
            date_observed = now - timedelta(days=days_ago)

            # Add small random jitter to coordinates (±0.05 degrees)
            lat = data["latitude"] + random.uniform(-0.05, 0.05)
            lon = data["longitude"] + random.uniform(-0.05, 0.05)

            confidence = round(random.uniform(0.75, 0.99), 2)
            ai_identified = idx in ai_identified_indices

            obs = Observation.objects.create(
                species_name=data["species_name"],
                category=data["category"],
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                date_observed=date_observed,
                notes=data["notes"],
                image="",
                prediction_method="DeepSeek Vision" if ai_identified else "Manual",
                prediction_confidence=confidence if ai_identified else 0.0,
                species_details=data["notes"][:200],
                ai_identified=ai_identified,
            )

            self.stdout.write(
                f"  [{idx + 1:02d}/22] ✅ {obs.species_name} "
                f"({data['category']}) — {data['city']}"
            )

        self.stdout.write(
            self.style.SUCCESS("\n✅ Seeded 22 observations successfully")
        )
