import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils.timezone import make_aware
from datetime import datetime
from observations.models import Observation

observations = [
    {
        "species_name": "Peregrine Falcon",
        "latitude": 33.7294,
        "longitude": 73.0931,
        "date_observed": "2025-03-10T08:15:00",
        "notes": "Spotted near Margalla Hills, perched on a rocky ledge.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.95,
        "species_details": "Peregrine Falcon (Falco peregrinus) is the fastest bird on Earth, reaching speeds over 300 km/h in a dive. Found in open habitats near cliffs. Least Concern globally but monitored in Pakistan due to habitat pressure.",
    },
    {
        "species_name": "Rhesus Macaque",
        "latitude": 33.7415,
        "longitude": 73.0812,
        "date_observed": "2025-03-12T10:30:00",
        "notes": "Group of 6 individuals foraging near Trail 3, Margalla Hills.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.98,
        "species_details": "Rhesus Macaque (Macaca mulatta) is a highly adaptable primate common in Islamabad's Margalla Hills. Listed as Least Concern but faces pressure from urban encroachment and feeding by tourists.",
    },
    {
        "species_name": "Indian Peacock",
        "latitude": 33.7198,
        "longitude": 73.0654,
        "date_observed": "2025-03-15T07:45:00",
        "notes": "Male displaying plumage near Rawal Lake shore.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.99,
        "species_details": "Indian Peacock (Pavo cristatus) is the national bird of India and commonly spotted around Rawal Lake, Islamabad. Least Concern. Thrives in semi-forested areas near water.",
    },
    {
        "species_name": "Himalayan Vulture",
        "latitude": 33.7512,
        "longitude": 73.1023,
        "date_observed": "2025-03-18T13:00:00",
        "notes": "Circling high above Margalla ridge, likely 3 individuals.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.91,
        "species_details": "Himalayan Vulture (Gyps himalayensis) is one of the largest Old World vultures. Near Threatened. Plays a critical role as a scavenger in mountain ecosystems. Seen regularly over Margalla Hills in winter.",
    },
    {
        "species_name": "Indian Crested Porcupine",
        "latitude": 33.7356,
        "longitude": 73.0778,
        "date_observed": "2025-04-02T19:30:00",
        "notes": "Nocturnal sighting near hiking trail, quills clearly visible.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.87,
        "species_details": "Indian Crested Porcupine (Hystrix indica) is a large rodent found in Margalla Hills. Least Concern. Nocturnal and herbivorous, it plays a role in seed dispersal and soil aeration.",
    },
    {
        "species_name": "Common Kingfisher",
        "latitude": 33.7089,
        "longitude": 73.0601,
        "date_observed": "2025-04-05T08:00:00",
        "notes": "Perched on a branch over Rawal Lake, vivid blue plumage.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.96,
        "species_details": "Common Kingfisher (Alcedo atthis) is a small, brilliantly colored bird found near freshwater bodies. Least Concern. Frequently spotted at Rawal Lake, Islamabad. Sensitive to water pollution.",
    },
    {
        "species_name": "Indian Grey Mongoose",
        "latitude": 33.7267,
        "longitude": 73.0845,
        "date_observed": "2025-04-08T11:20:00",
        "notes": "Darting across the path near Shakarparian Park.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.89,
        "species_details": "Indian Grey Mongoose (Herpestes edwardsii) is a small carnivore common in Islamabad's green zones. Least Concern. Known for its agility and ability to kill venomous snakes.",
    },
    {
        "species_name": "Cheer Pheasant",
        "latitude": 33.7601,
        "longitude": 73.1145,
        "date_observed": "2025-04-11T07:10:00",
        "notes": "Rare sighting on upper Margalla trail, pair observed.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.82,
        "species_details": "Cheer Pheasant (Catreus wallichii) is a Vulnerable species found in the Margalla Hills. Threatened by habitat loss and hunting. Its presence in Islamabad is considered ecologically significant.",
    },
    {
        "species_name": "Smooth-coated Otter",
        "latitude": 33.7045,
        "longitude": 73.0555,
        "date_observed": "2025-04-14T06:50:00",
        "notes": "Spotted swimming near the inlet stream of Rawal Lake.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.84,
        "species_details": "Smooth-coated Otter (Lutrogale perspicillata) is a Vulnerable species. Occasionally seen at Rawal Lake. Highly sensitive to water quality and human disturbance. Indicator of healthy aquatic ecosystems.",
    },
    {
        "species_name": "Rose-ringed Parakeet",
        "latitude": 33.7182,
        "longitude": 73.0712,
        "date_observed": "2025-04-20T09:00:00",
        "notes": "Flock of ~20 birds roosting in trees near F-6 sector.",
        "prediction_method": "Manual",
        "prediction_confidence": 0.97,
        "species_details": "Rose-ringed Parakeet (Psittacula krameri) is one of the most common parrots in Islamabad. Least Concern. Highly adaptable to urban environments. Often seen in large noisy flocks in residential areas.",
    },
]

created = 0
for data in observations:
    dt = make_aware(datetime.fromisoformat(data.pop("date_observed")))
    obs, made = Observation.objects.get_or_create(
        species_name=data["species_name"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        defaults={**data, "date_observed": dt, "image": "observations/sample.png"}
    )
    if made:
        created += 1

print(f"Done. {created} new observations created, {len(observations) - created} already existed.")
