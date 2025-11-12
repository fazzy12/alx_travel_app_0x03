import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from listings.models import Listing, Booking, Review
from django.db import transaction

# Sample data instead of using Faker
FIRST_NAMES = [
    'John', 'Jane', 'Mike', 'Sarah', 'David', 'Emma', 'Chris', 'Lisa', 'Tom', 'Anna',
    'James', 'Mary', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson'
]


class Command(BaseCommand):
    help = 'Seed the database with sample listings data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--users', 
            type=int, 
            default=20, 
            help='Number of users to create (default: 20)'
        )
        parser.add_argument(
            '--listings', 
            type=int, 
            default=15, 
            help='Number of listings to create (default: 15)'
        )
        parser.add_argument(
            '--bookings', 
            type=int, 
            default=30, 
            help='Number of bookings to create (default: 30)'
        )
        parser.add_argument(
            '--reviews', 
            type=int, 
            default=25, 
            help='Number of reviews to create (default: 25)'
        )
        parser.add_argument(
            '--clear', 
            action='store_true', 
            help='Clear existing data before seeding'
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(
                self.style.WARNING('Clearing existing data...')
            )
            self.clear_data()
        
        try:
            with transaction.atomic():
                self.stdout.write('Starting database seeding...')
                
                # Create users
                users = self.create_users(options['users'])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {len(users)} users')
                )
                
                # Create listings
                listings = self.create_listings(users, options['listings'])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {len(listings)} listings')
                )
                
                # Create bookings
                bookings = self.create_bookings(users, listings, options['bookings'])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {len(bookings)} bookings')
                )
                
                # Create reviews
                reviews = self.create_reviews(users, listings, options['reviews'])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {len(reviews)} reviews')
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nDatabase seeding completed successfully!\n'
                        f'Created:\n'
                        f'  - {len(users)} users\n'
                        f'  - {len(listings)} listings\n'
                        f'  - {len(bookings)} bookings\n'
                        f'  - {len(reviews)} reviews'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during seeding: {str(e)}')
            )
            raise
    
    def clear_data(self):
        """Clear existing data from all tables"""
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Listing.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()  # Keep superusers
        self.stdout.write(self.style.SUCCESS('✓ Existing data cleared'))
    
    def create_users(self, count):
        """Create sample users"""
        users = []
        used_usernames = set()
        used_emails = set()
        
        for i in range(count):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            
            # Generate unique username
            base_username = f"{first_name.lower()}{last_name.lower()}{i}"
            username = base_username
            counter = 1
            while username in used_usernames:
                username = f"{base_username}{counter}"
                counter += 1
            used_usernames.add(username)
            
            # Generate unique email
            email = f"{username}@example.com"
            while email in used_emails:
                email = f"{username}{random.randint(1, 999)}@example.com"
            used_emails.add(email)
            
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
            user.set_password('password123')  # Default password for all users
            users.append(user)
        
        User.objects.bulk_create(users)
        return User.objects.filter(is_superuser=False)
    
    def create_listings(self, users, count):
        """Create sample property listings"""
        property_types = [
            'Cozy Apartment', 'Luxury Villa', 'Modern Loft', 'Beach House',
            'Mountain Cabin', 'City Studio', 'Country Cottage', 'Penthouse',
            'Townhouse', 'Historic Home'
        ]
        
        cities = [
            'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX',
            'Phoenix, AZ', 'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA',
            'Dallas, TX', 'San Jose, CA', 'Austin, TX', 'Jacksonville, FL',
            'Fort Worth, TX', 'Columbus, OH', 'Charlotte, NC', 'San Francisco, CA'
        ]
        
        listings = []
        for i in range(count):
            host = random.choice(users)
            property_type = random.choice(property_types)
            city = random.choice(cities)
            
            listing = Listing(
                host_id=host,
                name=f"{property_type} in {city.split(',')[0]}",
                description=self.generate_property_description(property_type, city),
                location=city,
                price_per_night=Decimal(str(random.randint(50, 500))),
            )
            listings.append(listing)
        
        Listing.objects.bulk_create(listings)
        return Listing.objects.all()
    
    def generate_property_description(self, property_type, city):
        """Generate realistic property descriptions"""
        amenities = [
            'WiFi', 'Kitchen', 'Air conditioning', 'Heating', 'Parking',
            'Pool', 'Gym', 'Balcony', 'Garden', 'Hot tub', 'Fireplace',
            'TV', 'Washer', 'Dryer'
        ]
        
        selected_amenities = random.sample(amenities, k=random.randint(3, 6))
        amenities_text = ', '.join(selected_amenities)
        
        return (f"Beautiful {property_type.lower()} located in {city.split(',')[0]}. "
                f"This property features {amenities_text}. Perfect for travelers looking "
                f"for comfort and convenience. Close to major attractions and public transportation.")
    
    def create_bookings(self, users, listings, count):
        """Create sample bookings"""
        bookings = []
        statuses = ['pending', 'confirmed', 'canceled']
        status_weights = [0.2, 0.7, 0.1]  # 20% pending, 70% confirmed, 10% canceled
        
        for i in range(count):
            user = random.choice(users)
            listing = random.choice(listings)
            
            # Generate random start date (within next 6 months)
            start_date = date.today() + timedelta(days=random.randint(1, 180))
            
            # Generate end date (1-14 days after start date)
            end_date = start_date + timedelta(days=random.randint(1, 14))
            
            # Calculate total price
            nights = (end_date - start_date).days
            total_price = listing.price_per_night * nights
            
            booking = Booking(
                property_id=listing,
                user_id=user,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                status=random.choices(statuses, weights=status_weights)[0],
            )
            bookings.append(booking)
        
        Booking.objects.bulk_create(bookings)
        return Booking.objects.all()
    
    def create_reviews(self, users, listings, count):
        """Create sample reviews"""
        reviews = []
        review_comments = [
            "Amazing place! Highly recommended.",
            "Great location and very clean. Would stay again.",
            "Perfect for a weekend getaway. Host was very responsive.",
            "Beautiful property with all amenities as described.",
            "Good value for money. Close to all attractions.",
            "Lovely place, felt like home. Great experience.",
            "Excellent host and wonderful property. 5 stars!",
            "Very comfortable and well-equipped. Enjoyed our stay.",
            "Nice place but could use some updates. Overall good.",
            "Outstanding property! Exceeded our expectations."
        ]
        
        created_reviews = set()  # To avoid duplicate reviews from same user for same property
        
        for i in range(count):
            attempts = 0
            while attempts < 50:  # Prevent infinite loop
                user = random.choice(users)
                listing = random.choice(listings)
                
                # Check if this user already reviewed this property
                if (user.id, listing.listing_id) not in created_reviews:
                    review = Review(
                        property_id=listing,
                        user_id=user,
                        rating=random.randint(1, 5),
                        comment=random.choice(review_comments),
                    )
                    reviews.append(review)
                    created_reviews.add((user.id, listing.listing_id))
                    break
                
                attempts += 1
        
        Review.objects.bulk_create(reviews)
        return Review.objects.all()