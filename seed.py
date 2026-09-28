from app import app, db
from models import Event, Registration
from datetime import datetime, date, time
import random

def seed_events():
    events_data = [
        ("TechNova 2026", "The biggest annual hackathon of our college. Collaborate, innovate, and win prizes!", "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=800&q=80"),
        ("Rhythms Night", "A night of musical brilliance featuring student bands and guest artists.", "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=800&q=80"),
        ("AI & Future Workshop", "Hands-on workshop on Generative AI and its impact on the industry.", "https://images.unsplash.com/photo-1485083269755-a7b559a4fe5e?auto=format&fit=crop&w=800&q=80"),
        ("Pixel Perfect", "Photography competition followed by a masterclass from professionals.", "https://images.unsplash.com/photo-1452587925148-ce544e77e70d?auto=format&fit=crop&w=800&q=80"),
        ("Debate Duel", "Inter-college debate championship on current socio-economic topics.", "https://loremflickr.com/800/600/debate"),
        ("Code Rush", "Fast-paced competitive programming contest. May the best logic win!", "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=800&q=80"),
        ("Cultural Fest '26", "A celebration of diversity through dance, drama, and regional stalls.", "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=800&q=80"),
        ("StartUp Pitch", "Got an idea? Pitch it to investors and mentors in this shark-tank style event.", "https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=800&q=80"),
        ("ESports League", "Compete in Valorant and FIFA for the campus championship title.", "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80"),
        ("RoboWars", "Custom-built robots fighting for supremacy in the arena.", "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=80"),
        ("Open Mic Poetry", "Express your soul through words in a cozy cafe-style setting.", "https://images.unsplash.com/photo-1506466010722-395aa2bef877?auto=format&fit=crop&w=800&q=80"),
        ("Science Expo", "Exhibition of breakthrough student projects in core engineering fields.", "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=800&q=80"),
        ("Fitness Mania", "Morning yoga, crossfit, and healthy lifestyle seminars.", "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=800&q=80"),
        ("Movie Night", "Classic cinema screening under the stars at the football ground.", "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80"),
        ("Alumni Meet", "Gala dinner and networking session with our distinguished alumni.", "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=800&q=80"),
        ("Cloud Summit", "AWS and Azure experts sharing insights on cloud infrastructure.", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80"),
        ("Design Sprint", "24-hour UI/UX challenge to solve problems for local non-profits.", "https://images.unsplash.com/photo-1558655146-d09347e92766?auto=format&fit=crop&w=800&q=80")
    ]

    venues = ["Main Auditorium", "Tech Block Seminar Hall", "Student Center", "Football Ground", "Cafe Terrace", "Library Hall B"]
    
    with app.app_context():
        # Clear existing data in correct order (FK constraints)
        Registration.query.delete()
        Event.query.delete()
        
        for name, desc, img in events_data:
            event = Event(
                name=name,
                description=desc,
                date=date(2026, random.randint(5, 12), random.randint(1, 28)),
                time=time(random.randint(9, 20), 0),
                venue=random.choice(venues),
                image_url=img
            )
            db.session.add(event)
        
        db.session.commit()
        print(f"Successfully seeded {len(events_data)} events!")

if __name__ == "__main__":
    seed_events()
