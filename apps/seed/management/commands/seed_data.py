import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker
from apps.accounts.models import VenueProfile, CreatorProfile
from apps.spaces.models import Space, SpaceImage, Availability, SpaceAttachment
from apps.proposals.models import Proposal, PortfolioProject, PortfolioImage
from apps.bookings.models import Booking
from apps.reviews.models import Review
from apps.events.models import Event, Story
from apps.follows.models import Follow

User = get_user_model()
fake = Faker()

VENUE_DATA = [
    {"name": "The Whitespace Gallery", "type": "gallery", "city": "New York", "state": "NY", "country": "US", "lat": 40.7484, "lng": -73.9856},
    {"name": "Lumiere Museum of Digital Art", "type": "museum", "city": "Los Angeles", "state": "CA", "country": "US", "lat": 34.0522, "lng": -118.2437},
    {"name": "Nordic Cultural House", "type": "cultural_house", "city": "Chicago", "state": "IL", "country": "US", "lat": 41.8781, "lng": -87.6298},
    {"name": "The Void Theater", "type": "theater", "city": "San Francisco", "state": "CA", "country": "US", "lat": 37.7749, "lng": -122.4194},
    {"name": "Prism Contemporary", "type": "gallery", "city": "Miami", "state": "FL", "country": "US", "lat": 25.7617, "lng": -80.1918},
    {"name": "Aurora Arts Center", "type": "cultural_house", "city": "Austin", "state": "TX", "country": "US", "lat": 30.2672, "lng": -97.7431},
    {"name": "The Glass Pavilion", "type": "gallery", "city": "Seattle", "state": "WA", "country": "US", "lat": 47.6062, "lng": -122.3321},
    {"name": "Nexus Museum", "type": "museum", "city": "Boston", "state": "MA", "country": "US", "lat": 42.3601, "lng": -71.0589},
    {"name": "Echospace Studios", "type": "studio", "city": "Portland", "state": "OR", "country": "US", "lat": 45.5152, "lng": -122.6784},
    {"name": "The Atrium Gallery", "type": "gallery", "city": "Denver", "state": "CO", "country": "US", "lat": 39.7392, "lng": -104.9903},
    {"name": "Meridian Cultural Center", "type": "cultural_house", "city": "Nashville", "state": "TN", "country": "US", "lat": 36.1627, "lng": -86.7816},
    {"name": "Hyperion Art Space", "type": "gallery", "city": "Brooklyn", "state": "NY", "country": "US", "lat": 40.6782, "lng": -73.9442},
    {"name": "The Digital Cathedral", "type": "museum", "city": "Washington", "state": "DC", "country": "US", "lat": 38.9072, "lng": -77.0369},
    {"name": "Solaris Theater", "type": "theater", "city": "Philadelphia", "state": "PA", "country": "US", "lat": 39.9526, "lng": -75.1652},
    {"name": "Flux Art House", "type": "cultural_house", "city": "Detroit", "state": "MI", "country": "US", "lat": 42.3314, "lng": -83.0458},
]

CREATOR_DATA = [
    {"name": "Hyperreal Studios", "specialty": "vr", "skills": ["Unity", "Unreal Engine", "Blender", "C#"]},
    {"name": "Void Interactive", "specialty": "interactive", "skills": ["TouchDesigner", "Arduino", "Processing", "OpenCV"]},
    {"name": "Lumina XR Collective", "specialty": "mr", "skills": ["Unity", "ARKit", "ARCore", "Hololens"]},
    {"name": "Neon Dreams Lab", "specialty": "projection", "skills": ["MadMapper", "Resolume", "After Effects", "Cinema 4D"]},
    {"name": "Synapse Digital", "specialty": "vr", "skills": ["Unreal Engine", "Maya", "Substance Painter", "C++"]},
    {"name": "Ethereal Arts", "specialty": "immersive", "skills": ["Unity", "FMOD", "Blender", "Shader Graph"]},
    {"name": "Pixel Forge Studio", "specialty": "ar", "skills": ["ARKit", "Swift", "Spark AR", "8th Wall"]},
    {"name": "Chromatic Visions", "specialty": "projection", "skills": ["TouchDesigner", "Notch", "Resolume", "Kinect"]},
    {"name": "Quantum Space Lab", "specialty": "vr", "skills": ["Unity", "Unreal Engine", "Oculus SDK", "WebXR"]},
    {"name": "Atlas Immersive", "specialty": "immersive", "skills": ["Unity", "Wwise", "Blender", "Python"]},
    {"name": "Spectra Interactive", "specialty": "interactive", "skills": ["openFrameworks", "Arduino", "Raspberry Pi", "MaxMSP"]},
    {"name": "Horizon XR", "specialty": "mr", "skills": ["Unity", "Vuforia", "Azure Spatial Anchors", "C#"]},
    {"name": "Pulse Digital Art", "specialty": "immersive", "skills": ["TouchDesigner", "Ableton", "Cinema 4D", "Houdini"]},
    {"name": "Vertex Studios", "specialty": "vr", "skills": ["Unreal Engine", "ZBrush", "Substance 3D", "MetaHuman"]},
    {"name": "Aether Collective", "specialty": "projection", "skills": ["MadMapper", "Millumin", "After Effects", "Blender"]},
    {"name": "Nova Interactive", "specialty": "ar", "skills": ["Unity", "ARCore", "Niantic Lightship", "Flutter"]},
    {"name": "Drift Studio", "specialty": "interactive", "skills": ["Processing", "p5.js", "Three.js", "WebGL"]},
    {"name": "Cipher Arts", "specialty": "immersive", "skills": ["Unity", "FMOD", "Photogrammetry", "LiDAR"]},
    {"name": "Prism XR Lab", "specialty": "vr", "skills": ["Unity", "SteamVR", "Hand Tracking", "Eye Tracking"]},
    {"name": "Echo Digital", "specialty": "interactive", "skills": ["TouchDesigner", "Kinect", "RealSense", "Python"]},
]

SPACE_TYPES = ['gallery_room', 'main_hall', 'outdoor', 'theater', 'lobby', 'studio', 'entire_venue']

GALLERY_IMAGES = [
    "https://images.unsplash.com/photo-1572947650440-e8a97ef053b2?w=800",
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=800",
    "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=800",
    "https://images.unsplash.com/photo-1577083288073-40892c0860a4?w=800",
    "https://images.unsplash.com/photo-1554907984-15263bfd63bd?w=800",
    "https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=800",
    "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=800",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800",
    "https://images.unsplash.com/photo-1541367777708-7905fe3296c0?w=800",
    "https://images.unsplash.com/photo-1605429523419-d828acb941d9?w=800",
    "https://images.unsplash.com/photo-1594732832278-abd644401426?w=800",
    "https://images.unsplash.com/photo-1620503374956-c942862f0372?w=800",
    "https://images.unsplash.com/photo-1574610758891-5b809b6e6e2c?w=800",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
    "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=800",
    "https://images.unsplash.com/photo-1459767129954-1b1c1f9b9ace?w=800",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=800",
]

PORTFOLIO_IMAGES = [
    "https://images.unsplash.com/photo-1633356122102-3fe601e05bd2?w=800",
    "https://images.unsplash.com/photo-1626379953822-baec19c3accd?w=800",
    "https://images.unsplash.com/photo-1592478411213-6153e4ebc07d?w=800",
    "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=800",
    "https://images.unsplash.com/photo-1614624532983-4ce03382d63d?w=800",
    "https://images.unsplash.com/photo-1618005198919-d3d4b5a92ead?w=800",
    "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800",
    "https://images.unsplash.com/photo-1608501078713-8e445a709b39?w=800",
    "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?w=800",
    "https://images.unsplash.com/photo-1617791160505-6f00504e3519?w=800",
]

AVATAR_IMAGES = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200",
    "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=200",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200",
]

PORTFOLIO_TITLES = [
    "The Memory Palace - VR Installation",
    "Augmented Ruins - AR Museum Experience",
    "Digital Ecosystem - Interactive Bio Art",
    "Echoes of Light - Projection Mapping",
    "Neural Landscapes - Immersive Environment",
    "Quantum Garden - Mixed Reality",
    "Synesthetic Symphony - Audio-Visual XR",
    "Time Capsule - VR Documentary",
    "Urban Mirage - AR Street Art",
    "Voices of the Deep - Underwater VR",
    "Crystal Caverns - Room-Scale VR",
    "Data Sculpture - Interactive Installation",
    "Phantom Architectures - AR Exhibition",
    "Sonic Bloom - Sound-Reactive Projection",
    "Terra Incognita - Immersive Theater",
    "Woven Light - Fiber Optic Installation",
    "Zero Gravity - VR Dance Experience",
    "Chromatic Dreams - 360° Projection",
    "Living Walls - AR Murals",
    "Pulse - Biometric Interactive Art",
]

EVENT_COVERS = [
    'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?w=1200',
    'https://images.unsplash.com/photo-1531058020387-3be344556be6?w=1200',
    'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1200',
    'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1200',
    'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=1200',
    'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=1200',
    'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=1200',
    'https://images.unsplash.com/photo-1505236858219-8359eb29e329?w=1200',
    'https://images.unsplash.com/photo-1542037104857-ffbb0b9155fb?w=1200',
    'https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=1200',
]

STORY_IMAGES = [
    'https://images.unsplash.com/photo-1533158326339-7f3cf2404354?w=800',
    'https://images.unsplash.com/photo-1551818255-e6e10975bc17?w=800',
    'https://images.unsplash.com/photo-1536924940846-227afb31e2a5?w=800',
    'https://images.unsplash.com/photo-1567095761054-7a02e69e5c43?w=800',
    'https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=800',
    'https://images.unsplash.com/photo-1561489413-985b06da5bee?w=800',
    'https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=800',
    'https://images.unsplash.com/photo-1541535650810-10d26f5c2ab3?w=800',
    'https://images.unsplash.com/photo-1541591970742-c9b18e7d5ed8?w=800',
    'https://images.unsplash.com/photo-1502635385003-ee1e6a1a742d?w=800',
    'https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?w=800',
    'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=800',
]

EVENT_TEMPLATES = [
    ('opening', 'Spring Opening: {theme}', 'Join us for the opening reception of our new exhibition exploring {theme}. Light refreshments and conversations with the artists.'),
    ('performance', 'Live Performance: {theme}', 'An evening of immersive performance art centered on {theme}. Limited seating, early arrival recommended.'),
    ('workshop', 'Hands-on Workshop: {theme}', 'Join our intimate workshop on {theme}. All materials provided. Ideal for beginners and experienced creators alike.'),
    ('installation', 'Installation Preview: {theme}', 'Preview our new multi-room installation investigating {theme}. Walk-through tours on the half-hour.'),
    ('residency', 'Open Studios: {theme}', 'Meet our resident artists working on {theme}. Studios will be open to the public for this special event.'),
    ('exhibition', 'Exhibition: {theme}', 'A group show featuring new work on {theme} by emerging and established artists.'),
    ('screening', 'Screening Night: {theme}', 'Curated screening of short films exploring {theme}, followed by a Q&A with the filmmakers.'),
]

EVENT_THEMES = [
    'Light and Time', 'Memory Palace', 'Digital Bodies', 'Synthetic Nature', 'Parallel Worlds',
    'Liquid Architecture', 'Quiet Machines', 'The Color of Sound', 'Ritual and Repetition',
    'Unstable Ground', 'Invisible Cities', 'After the Algorithm', 'Touch and Distance',
    'Slow Futures', 'Post-Natural', 'Spectral Objects', 'Resonance', 'Field Studies',
]

STORY_CAPTIONS = [
    'Setting up for tonight', '',  # empty for variety
    'Behind the scenes 🎨', 'Work in progress',
    'Last details before opening', 'The space is ready',
    'New piece just arrived', 'Testing the lights',
    'First day of install', "Tomorrow's the day",
    'Final rehearsal', 'Almost there',
    'Come see us this weekend', 'Open now through Sunday',
    '', 'Studio vibes today',
]

REVIEW_COMMENTS = [
    "Incredible space that perfectly suited our VR installation. The technical infrastructure was top-notch.",
    "The venue team was extremely accommodating. Great blackout capabilities for our projection mapping.",
    "Beautiful gallery space with excellent natural lighting. Perfect for our AR experience.",
    "Amazing collaboration! The space exceeded our expectations for the immersive theater piece.",
    "Professional venue with all the technical requirements we needed. Will definitely book again.",
    "The main hall was stunning. Great acoustics and plenty of power outlets for our interactive installation.",
    "Wonderful cultural house with a fantastic team. They really understood our artistic vision.",
    "Perfect studio space for prototyping. The WiFi was reliable and the climate control was essential.",
    "Outstanding theater venue. The sound system and blackout capabilities were exactly what we needed.",
    "Great outdoor space for our large-scale projection. The venue provided excellent support throughout.",
    "The gallery room was intimate and perfect for our mixed reality experience. Highly recommend.",
    "Excellent venue management. They helped us with every technical challenge during setup.",
]


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing data...')
        Follow.objects.all().delete()
        Story.objects.all().delete()
        Event.objects.all().delete()
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Proposal.objects.all().delete()
        PortfolioImage.objects.all().delete()
        PortfolioProject.objects.all().delete()
        Availability.objects.all().delete()
        SpaceAttachment.objects.all().delete()
        SpaceImage.objects.all().delete()
        Space.objects.all().delete()
        CreatorProfile.objects.all().delete()
        VenueProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write('Creating venues...')
        venues = self._create_venues()
        self.stdout.write(f'  Created {len(venues)} venues')

        self.stdout.write('Creating creators...')
        creators = self._create_creators()
        self.stdout.write(f'  Created {len(creators)} creators')

        self.stdout.write('Creating spaces...')
        spaces = self._create_spaces(venues)
        self.stdout.write(f'  Created {len(spaces)} spaces')

        self.stdout.write('Creating portfolio projects...')
        projects = self._create_portfolios(creators)
        self.stdout.write(f'  Created {len(projects)} portfolio projects')

        self.stdout.write('Creating proposals...')
        proposals = self._create_proposals(creators, spaces)
        self.stdout.write(f'  Created {len(proposals)} proposals')

        self.stdout.write('Creating bookings...')
        bookings = self._create_bookings(proposals)
        self.stdout.write(f'  Created {len(bookings)} bookings')

        self.stdout.write('Creating reviews...')
        reviews = self._create_reviews(bookings)
        self.stdout.write(f'  Created {len(reviews)} reviews')

        self.stdout.write('Creating events...')
        events = self._create_events(venues, creators, spaces)
        self.stdout.write(f'  Created {len(events)} events')

        self.stdout.write('Creating stories...')
        stories = self._create_stories(venues, creators, spaces, events)
        self.stdout.write(f'  Created {len(stories)} stories')

        self.stdout.write('Creating follow graph...')
        follows = self._create_follows(venues, creators)
        self.stdout.write(f'  Created {len(follows)} follow relationships')

        # Mark some as featured
        for space in random.sample(list(spaces), min(8, len(spaces))):
            space.is_featured = True
            space.save()
        for creator in random.sample(list(creators), min(6, len(creators))):
            creator.is_featured = True
            creator.save()

        self.stdout.write(self.style.SUCCESS('Seed data created successfully!'))

    def _create_venues(self):
        venues = []
        for i, vd in enumerate(VENUE_DATA):
            user = User.objects.create_user(
                username=f"venue_{i+1}",
                email=f"venue{i+1}@cultureconnect.com",
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role='venue',
                avatar=random.choice(AVATAR_IMAGES),
                bio=fake.paragraph(nb_sentences=3),
                is_verified=True,
            )
            profile = VenueProfile.objects.create(
                user=user,
                organization_name=vd['name'],
                organization_type=vd['type'],
                address=fake.street_address(),
                city=vd['city'],
                state=vd['state'],
                country=vd['country'],
                zip_code=fake.zipcode(),
                latitude=vd['lat'],
                longitude=vd['lng'],
                description=fake.paragraph(nb_sentences=5),
                logo=f"https://ui-avatars.com/api/?name={vd['name'].replace(' ', '+')}&size=200&background=6366f1&color=fff",
                cover_image=random.choice(GALLERY_IMAGES),
                walkability_score=random.randint(60, 98),
                transit_score=random.randint(50, 100),
                bike_score=random.randint(40, 90),
                parking_info=random.choice([
                    'Street parking available', 'On-site parking garage (200 spots)',
                    'Valet parking available', 'Public parking lot nearby',
                    'Underground parking (50 spots)', 'Metered street parking',
                ]),
                nearby_transit=[
                    {"name": f"{random.choice(['Central','Main','Park','Arts','Museum'])} Station",
                     "lines": random.sample(["A","B","C","D","E","1","2","3","L","N","R"], k=random.randint(2, 4)),
                     "type": "subway", "walk_min": random.randint(2, 8)},
                    {"name": f"{random.choice(['Broadway','5th Ave','Market','State'])} Stop",
                     "lines": random.sample(["Bus 10","Bus 22","Bus 45","Bus 7","Express"], k=random.randint(1, 3)),
                     "type": "bus", "walk_min": random.randint(1, 5)},
                    {"name": f"{vd['city']} Central",
                     "lines": ["Regional Rail"], "type": "rail", "walk_min": random.randint(8, 15)},
                ],
            )
            venues.append(profile)
        return venues

    def _create_creators(self):
        creators = []
        cities = ['New York', 'Los Angeles', 'London', 'Berlin', 'Tokyo', 'Amsterdam', 'Barcelona', 'San Francisco', 'Austin', 'Portland']
        for i, cd in enumerate(CREATOR_DATA):
            user = User.objects.create_user(
                username=f"creator_{i+1}",
                email=f"creator{i+1}@cultureconnect.com",
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role='creator',
                avatar=random.choice(AVATAR_IMAGES),
                bio=fake.paragraph(nb_sentences=4),
                is_verified=True,
            )
            profile = CreatorProfile.objects.create(
                user=user,
                display_name=cd['name'],
                specialty=cd['specialty'],
                skills=cd['skills'],
                portfolio_url=f"https://{cd['name'].lower().replace(' ', '')}.com",
                years_experience=random.randint(2, 15),
                city=random.choice(cities),
                country='US',
            )
            creators.append(profile)
        return creators

    def _create_spaces(self, venues):
        spaces = []
        space_names = [
            "Main Gallery", "North Wing", "Grand Hall", "Studio A", "Rooftop Terrace",
            "The Black Box", "East Pavilion", "Media Lab", "Atrium Space", "Theater Hall",
            "South Gallery", "Workshop Room", "Exhibition Hall", "Outdoor Courtyard",
            "Innovation Lab", "Performance Space", "Digital Gallery", "Archive Room",
        ]
        tags_options = [
            ["immersive", "dark-room"], ["projection-ready", "large-scale"],
            ["tech-equipped", "interactive"], ["white-cube", "flexible"],
            ["outdoor", "weather-dependent"], ["theater", "seated"],
            ["studio", "intimate"], ["high-ceiling", "industrial"],
        ]

        for venue in venues:
            num_spaces = random.randint(2, 4)
            selected_names = random.sample(space_names, num_spaces)
            for name in selected_names:
                space_type = random.choice(SPACE_TYPES)
                area = random.randint(300, 5000)
                space = Space.objects.create(
                    venue=venue,
                    title=f"{name} at {venue.organization_name}",
                    description=fake.paragraph(nb_sentences=6),
                    space_type=space_type,
                    area_sqft=area,
                    ceiling_height_ft=Decimal(str(random.uniform(10, 30))).quantize(Decimal('0.1')),
                    max_capacity=random.randint(20, 500),
                    has_wifi=True,
                    has_power_outlets=True,
                    has_projection_surfaces=random.choice([True, True, False]),
                    has_sound_system=random.choice([True, False]),
                    has_blackout_capability=random.choice([True, True, False]),
                    has_climate_control=True,
                    technical_notes=fake.paragraph(nb_sentences=2),
                    daily_rate=Decimal(str(random.randint(200, 3000))),
                    weekly_rate=Decimal(str(random.randint(1000, 15000))),
                    monthly_rate=Decimal(str(random.randint(3000, 50000))),
                    currency='USD',
                    tags=random.choice(tags_options),
                    features={
                        "Access": random.sample(["24 Hour Access", "Controlled Access", "Loading Dock", "Freight Elevator", "ADA Accessible", "Street Level Entry"], k=random.randint(2, 4)),
                        "Technical": random.sample(["Fiber Optic Internet", "Dedicated Power Grid", "Pre-wired AV", "Rigging Points", "DMX Lighting", "Ethernet Drops", "GPU Rendering Farm"], k=random.randint(2, 5)),
                        "Comfort": random.sample(["Air Conditioning", "Heating", "Natural Light", "Skylights", "High Ceilings", "Kitchenette", "Restrooms", "Green Room"], k=random.randint(2, 5)),
                        "Production": random.sample(["Projection Surfaces", "Blackout Curtains", "Sound System", "Mixing Console", "Stage Lighting", "Fog Machine", "LED Wall"], k=random.randint(2, 4)),
                    },
                )
                # Add images
                imgs = random.sample(GALLERY_IMAGES, min(4, len(GALLERY_IMAGES)))
                for j, img_url in enumerate(imgs):
                    SpaceImage.objects.create(
                        space=space, image_url=img_url, is_primary=(j == 0), order=j,
                    )
                # Add availability
                today = date.today()
                for k in range(3):
                    start = today + timedelta(days=random.randint(k * 30, k * 30 + 20))
                    end = start + timedelta(days=random.randint(7, 30))
                    Availability.objects.create(
                        space=space, start_date=start, end_date=end, is_available=True,
                    )
                # Add attachments
                attachment_options = [
                    ("Floor Plan", "floor_plan"), ("Technical Spec Sheet", "spec_sheet"),
                    ("Venue Brochure", "brochure"), ("Safety Guidelines", "other"),
                ]
                for title, ftype in random.sample(attachment_options, k=random.randint(1, 3)):
                    SpaceAttachment.objects.create(
                        space=space, title=f"{title} - {name}",
                        file_url=f"https://example.com/docs/{space.slug}/{ftype}.pdf",
                        file_type=ftype,
                    )
                spaces.append(space)
        return spaces

    def _create_portfolios(self, creators):
        projects = []
        for creator in creators:
            num = random.randint(2, 5)
            titles = random.sample(PORTFOLIO_TITLES, num)
            for title in titles:
                proj = PortfolioProject.objects.create(
                    creator=creator,
                    title=title,
                    description=fake.paragraph(nb_sentences=4),
                    technology=creator.specialty,
                    year=random.randint(2020, 2026),
                    cover_image=random.choice(PORTFOLIO_IMAGES),
                    video_url="https://vimeo.com/example",
                    tags=random.sample(["immersive", "interactive", "VR", "AR", "projection", "installation", "sound", "light"], 3),
                )
                for j in range(random.randint(1, 3)):
                    PortfolioImage.objects.create(
                        project=proj, image_url=random.choice(PORTFOLIO_IMAGES), order=j,
                    )
                projects.append(proj)
        return projects

    def _create_proposals(self, creators, spaces):
        proposals = []
        statuses = ['submitted', 'submitted', 'under_review', 'accepted', 'accepted', 'rejected', 'withdrawn']
        for _ in range(35):
            creator = random.choice(creators)
            space = random.choice(spaces)
            start = date.today() + timedelta(days=random.randint(30, 180))
            end = start + timedelta(days=random.randint(7, 60))
            proposal = Proposal.objects.create(
                creator=creator,
                space=space,
                title=random.choice(PORTFOLIO_TITLES).split(' - ')[0] + " Experience",
                description=fake.paragraph(nb_sentences=5),
                project_type=creator.specialty,
                proposed_start_date=start,
                proposed_end_date=end,
                budget=Decimal(str(random.randint(5000, 100000))),
                technical_requirements=fake.paragraph(nb_sentences=2),
                audience_description=fake.paragraph(nb_sentences=2),
                status=random.choice(statuses),
            )
            proposals.append(proposal)
        return proposals

    def _create_bookings(self, proposals):
        bookings = []
        accepted = [p for p in proposals if p.status == 'accepted']
        booking_statuses = ['confirmed', 'confirmed', 'in_progress', 'completed', 'completed', 'completed']
        for proposal in accepted:
            days = (proposal.proposed_end_date - proposal.proposed_start_date).days
            total = proposal.space.daily_rate * days
            fee_venue = total * Decimal('0.08')
            fee_creator = total * Decimal('0.12')
            booking = Booking.objects.create(
                proposal=proposal,
                space=proposal.space,
                creator=proposal.creator,
                start_date=proposal.proposed_start_date,
                end_date=proposal.proposed_end_date,
                total_amount=total,
                platform_fee_venue=fee_venue,
                platform_fee_creator=fee_creator,
                status=random.choice(booking_statuses),
            )
            bookings.append(booking)
        return bookings

    def _create_reviews(self, bookings):
        reviews = []
        completed = [b for b in bookings if b.status == 'completed']
        for booking in completed:
            creator_user = booking.creator.user
            venue_user = booking.space.venue.user
            # Creator → Venue review (always)
            reviews.append(Review.objects.create(
                booking=booking,
                reviewer=creator_user,
                reviewee=venue_user,
                direction=Review.DIRECTION_CREATOR_TO_VENUE,
                rating=random.randint(3, 5),
                comment=random.choice(REVIEW_COMMENTS),
            ))
            # Venue → Creator review (70% of the time)
            if random.random() < 0.7:
                reviews.append(Review.objects.create(
                    booking=booking,
                    reviewer=venue_user,
                    reviewee=creator_user,
                    direction=Review.DIRECTION_VENUE_TO_CREATOR,
                    rating=random.randint(3, 5),
                    comment=random.choice(REVIEW_COMMENTS),
                ))
        return reviews

    def _create_events(self, venues, creators, spaces):
        events = []
        now = timezone.now()
        spaces_by_venue = {}
        for sp in spaces:
            spaces_by_venue.setdefault(sp.venue_id, []).append(sp)

        # Each venue hosts 2-4 events (mix past + upcoming)
        for venue in venues:
            venue_spaces = spaces_by_venue.get(venue.id, [])
            for _ in range(random.randint(2, 4)):
                type_key, title_tpl, desc_tpl = random.choice(EVENT_TEMPLATES)
                theme = random.choice(EVENT_THEMES)
                # 70% upcoming, 30% past
                if random.random() < 0.7:
                    offset = timedelta(days=random.randint(1, 45), hours=random.randint(0, 23))
                    starts_at = now + offset
                else:
                    offset = timedelta(days=random.randint(5, 60), hours=random.randint(0, 23))
                    starts_at = now - offset
                duration_hours = random.choice([2, 3, 4, 6, 24, 48, 72])
                ends_at = starts_at + timedelta(hours=duration_hours)
                event = Event.objects.create(
                    host=venue.user,
                    title=title_tpl.format(theme=theme),
                    event_type=type_key,
                    description=desc_tpl.format(theme=theme.lower()),
                    cover_image=random.choice(EVENT_COVERS),
                    starts_at=starts_at,
                    ends_at=ends_at,
                    space=random.choice(venue_spaces) if venue_spaces else None,
                    location_text='' if venue_spaces else f'{venue.city}, {venue.state}',
                    is_public=True,
                )
                events.append(event)

        # Each creator hosts 0-2 events (workshops, performances, open studios)
        creator_types = ['workshop', 'performance', 'residency', 'screening']
        for creator in creators:
            for _ in range(random.randint(0, 2)):
                type_key = random.choice(creator_types)
                title_tpl, desc_tpl = next(
                    ((t, d) for k, t, d in EVENT_TEMPLATES if k == type_key),
                    ('Event: {theme}', 'Join us for {theme}.')
                )
                theme = random.choice(EVENT_THEMES)
                offset = timedelta(days=random.randint(2, 30), hours=random.randint(0, 23))
                starts_at = now + offset
                ends_at = starts_at + timedelta(hours=random.choice([2, 3, 4]))
                event = Event.objects.create(
                    host=creator.user,
                    title=title_tpl.format(theme=theme),
                    event_type=type_key,
                    description=desc_tpl.format(theme=theme.lower()),
                    cover_image=random.choice(EVENT_COVERS),
                    starts_at=starts_at,
                    ends_at=ends_at,
                    location_text=f'{creator.city or "Online"}',
                    is_public=True,
                )
                events.append(event)

        # Create 1-2 LIVE events (started recently, still running)
        for venue in random.sample(list(venues), min(2, len(venues))):
            venue_spaces = spaces_by_venue.get(venue.id, [])
            type_key, title_tpl, desc_tpl = random.choice(EVENT_TEMPLATES)
            theme = random.choice(EVENT_THEMES)
            starts_at = now - timedelta(hours=1)
            ends_at = now + timedelta(hours=3)
            event = Event.objects.create(
                host=venue.user,
                title=title_tpl.format(theme=theme),
                event_type=type_key,
                description=desc_tpl.format(theme=theme.lower()),
                cover_image=random.choice(EVENT_COVERS),
                starts_at=starts_at,
                ends_at=ends_at,
                space=random.choice(venue_spaces) if venue_spaces else None,
                is_public=True,
            )
            events.append(event)

        return events

    def _create_stories(self, venues, creators, spaces, events):
        """Create active stories (within last 20h so they haven't expired)."""
        stories = []
        now = timezone.now()
        spaces_by_venue = {}
        for sp in spaces:
            spaces_by_venue.setdefault(sp.venue_id, []).append(sp)
        events_by_host = {}
        for ev in events:
            events_by_host.setdefault(ev.host_id, []).append(ev)

        # 60% of venues have a story
        for venue in random.sample(list(venues), int(len(venues) * 0.6)):
            n = random.randint(1, 3)
            for _ in range(n):
                hours_ago = random.randint(0, 20)
                created = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
                venue_events = events_by_host.get(venue.user_id, [])
                venue_spaces = spaces_by_venue.get(venue.id, [])
                story = Story.objects.create(
                    author=venue.user,
                    event=random.choice(venue_events) if venue_events and random.random() < 0.4 else None,
                    space=random.choice(venue_spaces) if venue_spaces and random.random() < 0.3 else None,
                    image=random.choice(STORY_IMAGES),
                    caption=random.choice(STORY_CAPTIONS),
                    expires_at=created + timedelta(hours=24),
                )
                # Override auto-set created_at
                Story.objects.filter(pk=story.pk).update(created_at=created)
                stories.append(story)

        # 50% of creators have a story
        for creator in random.sample(list(creators), int(len(creators) * 0.5)):
            n = random.randint(1, 2)
            for _ in range(n):
                hours_ago = random.randint(0, 20)
                created = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
                creator_events = events_by_host.get(creator.user_id, [])
                story = Story.objects.create(
                    author=creator.user,
                    event=random.choice(creator_events) if creator_events and random.random() < 0.4 else None,
                    image=random.choice(STORY_IMAGES),
                    caption=random.choice(STORY_CAPTIONS),
                    expires_at=created + timedelta(hours=24),
                )
                Story.objects.filter(pk=story.pk).update(created_at=created)
                stories.append(story)

        return stories

    def _create_follows(self, venues, creators):
        """Build a realistic follow graph. Each user follows ~30-60% of the others."""
        follows = []
        all_users = [v.user for v in venues] + [c.user for c in creators]
        for user in all_users:
            candidates = [u for u in all_users if u.id != user.id]
            n_follows = random.randint(
                max(2, int(len(candidates) * 0.3)),
                max(3, int(len(candidates) * 0.6)),
            )
            targets = random.sample(candidates, min(n_follows, len(candidates)))
            for target in targets:
                f, created = Follow.objects.get_or_create(follower=user, following=target)
                if created:
                    follows.append(f)
        return follows
