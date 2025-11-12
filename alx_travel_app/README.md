# ALX Travel App - Task 0x00

## Database Modeling and Data Seeding in Django

This project implements the database models, serializers, and seeding functionality for an AirBnB-like application as part of the ALX Travel App coursework.

## Project Structure

```
alx_travel_app/
├── listings/
│   ├── models.py              # Database models (Listing, Booking, Review)
│   ├── serializers.py         # API serializers (Listing, Booking)
│   ├── management/
│   │   └── commands/
│   │       └── seed.py        # Database seeding command
│   └── ...
├── README.md                  # This file
└── ...
```

## Models Implemented

### 1. Listing Model
- **listing_id**: Primary Key (UUID)
- **host_id**: Foreign Key to User
- **name**: Property name
- **description**: Property description
- **location**: Property location
- **price_per_night**: Decimal price
- **created_at/updated_at**: Timestamps

### 2. Booking Model
- **booking_id**: Primary Key (UUID)
- **property_id**: Foreign Key to Listing
- **user_id**: Foreign Key to User
- **start_date/end_date**: Booking dates
- **total_price**: Booking total cost
- **status**: Enum (pending, confirmed, canceled)
- **created_at**: Timestamp

### 3. Review Model
- **review_id**: Primary Key (UUID)
- **property_id**: Foreign Key to Listing
- **user_id**: Foreign Key to User
- **rating**: Integer (1-5)
- **comment**: Review text
- **created_at**: Timestamp

### 4. Payment Model (New)
- **payment_id**: Primary Key (UUID)
- **booking_id**: Foreign Key to Booking (OneToOne)
- **user_id**: Foreign Key to User
- **amount**: Decimal price
- **tx_ref**: Unique transaction reference (used for Chapa)
- **chapa_transaction_id**: Transaction ID from Chapa
- **status**: Enum (pending, completed, failed, canceled)
- **checkout_url**: URL to redirect user for payment
- **created_at/updated_at**: Timestamps

## Serializers

### ListingSerializer
- Handles all Listing model fields
- Validates price_per_night is positive
- Read-only fields: listing_id, created_at, updated_at

### BookingSerializer
- Handles all Booking model fields
- Validates end_date is after start_date
- Validates total_price is positive
- Read-only fields: booking_id, created_at

## Database Seeding

The seeding command populates the database with sample data for testing and development.

### Running the Seed Command

```bash
# Basic seeding with default values
python manage.py seed

# Custom quantities
python manage.py seed --users 50 --listings 30 --bookings 100 --reviews 80

# Clear existing data before seeding
python manage.py seed --clear

# Help
python manage.py seed --help
```

### Seed Command Options

- `--users`: Number of users to create (default: 20)
- `--listings`: Number of listings to create (default: 15)
- `--bookings`: Number of bookings to create (default: 30)
- `--reviews`: Number of reviews to create (default: 25)
- `--clear`: Clear existing data before seeding

### Sample Data Generated

- **Users**: Random users with realistic names, emails, and usernames
- **Listings**: Properties in various US cities with realistic descriptions and pricing
- **Bookings**: Reservations with random dates and calculated pricing
- **Reviews**: Property reviews with ratings and comments

## Chapa Payment Integration (Task 0x02)

The application is integrated with the **Chapa Payment Gateway** for handling booking payments.

### Setup and Credentials

1. Create a `.env` file and set the `CHAPA_SECRET_KEY` obtained from the Chapa developer portal. (The provided key is a test key: `CHASECK_TEST-2EGfvykfmNFpwwlUZCwmpW5IugMzKY23`)
2. Ensure the `requests` library is installed (`pip install requests`).
3. **Celery**: Celery is included in the requirements and is used to asynchronously send a confirmation email upon successful payment, which requires a separate Celery broker setup (e.g., RabbitMQ or Redis).


## Installation and Setup

1. Ensure you have the Django project set up
2. Install required dependencies:
   ```bash
   pip install faker
   ```
3. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
4. Seed the database:
   ```bash
   python manage.py seed
   ```

## Key Features

- **UUID Primary Keys**: All models use UUID for primary keys for better scalability
- **Data Validation**: Comprehensive validation in both models and serializers
- **Realistic Sample Data**: Uses Faker library to generate realistic test data
- **Indexed Fields**: Important fields are indexed for better query performance
- **Relationships**: Proper foreign key relationships between models
- **Constraints**: Database-level constraints for data integrity

## Usage

After seeding, you can:
- View the created data in Django admin
- Use the serializers in your API views
- Query the models in your application logic
- Test your application with realistic sample data

## Database Schema

The models follow the provided AirBnB database specification with appropriate:
- Primary and foreign key relationships
- Data types and constraints
- Indexing for performance
- Model methods and string representations

---

**Repository**: `alx_travel_app_0x01`  
**Directory**: `alx_travel_app`  
**Author**: ALX Student


### Payment Workflow

1.  A user sends a `POST` request to the `/api/bookings/` endpoint to create a booking.
2.  The application creates the `Booking` record and an initial `Payment` record with a `pending` status.
3.  The application calls the Chapa `/initialize` API using the `CHAPA_SECRET_KEY`.
4.  The API response returns the `Booking` details and a `payment_link` (the `checkout_url` from Chapa).
5.  The user is redirected to the `payment_link` to complete the transaction on Chapa's platform.
6.  Upon completion, Chapa redirects the user to the configured **callback URL**: `/api/payments/{tx_ref}/verify/`.
7.  The application calls the Chapa `/verify` API to confirm the transaction.
8.  On successful verification, the `Payment` status is set to `completed`, the `Booking` status is set to `confirmed`, and an asynchronous confirmation email is triggered (via a mock Celery task).
9.  If verification fails, the statuses are updated to `failed` or `canceled`.

## API Endpoints

The following RESTful API endpoints have been implemented using Django REST Framework ViewSets and Routers.

| Resource | Method | Endpoint | Description | Authentication |
| :--- | :--- | :--- | :--- | :--- |
| **Listings** | `GET` | `/api/listings/` | List all property listings. | None (AllowAny) |
| **Listings** | `POST` | `/api/listings/` | Create a new listing (Host). | Required (IsAuthenticated) |
| **Listing Detail**| `GET` | `/api/listings/{id}/` | Retrieve a specific listing. | None (AllowAny) |
| **Listing Detail**| `PUT`/`PATCH`/`DELETE`| `/api/listings/{id}/` | Update or Delete a listing. | Required (IsAuthenticated) |
| **Bookings** | `GET` | `/api/bookings/` | List all bookings. | Required (IsAuthenticated) |
| **Bookings** | `POST` | `/api/bookings/` | **Create a new booking and initiate Chapa payment.** Returns booking details and Chapa checkout link. | Required (IsAuthenticated) |
| **Booking Detail**| `GET`/`PUT`/`PATCH`/`DELETE`| `/api/bookings/{id}/` | Manage a specific booking. | Required (IsAuthenticated) |
| **Payments** | `GET` | `/api/payments/` | List all payment records for the authenticated user. | Required (IsAuthenticated) |
| **Payment Detail**| `GET` | `/api/payments/{tx_ref}/` | Retrieve a specific payment record by transaction reference. | Required (IsAuthenticated) |
| **Payment Verify**| `GET` | `/api/payments/{tx_ref}/verify/` | **Callback URL**: Verifies payment status with Chapa and updates Payment/Booking status. | None (AllowAny, internal verification check) |