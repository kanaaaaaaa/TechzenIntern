"""Rewrite fsq_category_labels in a Foursquare export CSV to a fixed, closed
set of store-finder-friendly category labels.

Usage:
    python3 backend/scripts/normalize_fsq_categories.py \
        backend/data/foursquare/danang_nearby_1000m.csv

The target CSV is overwritten in place; a ".bak" copy of the original is
written next to it first. A report of any category label found in the CSV
that isn't in CATEGORY_MAP (so it fell back to FALLBACK_CATEGORY) is printed
at the end.
"""

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

# Cells with multiple categories are written as a numpy array repr, e.g.
# "['A'\n 'B']" -- note there is no comma between items, so this is *not*
# valid Python list syntax (ast.literal_eval would silently merge adjacent
# quoted strings via Python's string-literal concatenation and produce a
# single garbled label). Pull out each quoted segment independently instead.
_LABEL_RE = re.compile(r"'((?:[^'\\]|\\.)*)'")

# The closed set of labels we want every row to use afterwards.
TARGET_CATEGORIES = [
    "restaurant", "cafe", "coffee_shop", "bakery", "bar", "meal_takeaway",
    "food_court", "dessert_shop", "ice_cream_shop", "convenience_store",
    "supermarket", "grocery_store", "department_store", "shopping_mall",
    "store", "market", "pharmacy", "drugstore", "gas_station", "parking",
    "hotel", "lodging", "movie_theater", "beauty_salon", "hair_salon",
    "barber_shop", "nail_salon", "laundry", "spa", "gym",
]

# Labels with no reasonable equivalent in TARGET_CATEGORIES (offices, civic
# buildings, schools, landmarks, medical, professional services, ...) are
# forced into this generic bucket, per the request to always pick the
# closest available label. Treat every mapping below to FALLBACK_CATEGORY as
# a low-confidence guess worth reviewing, not a real semantic match.
FALLBACK_CATEGORY = "store"

# Foursquare's full hierarchical label -> our target category.
# Built by hand from the 360 distinct labels observed in
# backend/data/foursquare/danang_nearby_1000m.csv.
CATEGORY_MAP = {
    # --- Dining and Drinking > Restaurant (all cuisines) -> restaurant ---
    "Dining and Drinking > Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Vietnamese Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Noodle Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Japanese Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Japanese Restaurant > Sushi Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Japanese Restaurant > Ramen Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Korean Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Korean Restaurant > Korean BBQ Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Chinese Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Chinese Restaurant > Dim Sum Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Chinese Restaurant > Taiwanese Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Chinese Restaurant > Szechuan Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Thai Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Hotpot Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Asian Restaurant > Malay Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Seafood Restaurant": "restaurant",
    "Dining and Drinking > Breakfast Spot": "restaurant",
    "Dining and Drinking > Restaurant > Pizzeria": "restaurant",
    "Dining and Drinking > Restaurant > Vegan and Vegetarian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > BBQ Joint": "restaurant",
    "Dining and Drinking > Restaurant > Sandwich Spot": "restaurant",
    "Dining and Drinking > Restaurant > Fried Chicken Joint": "restaurant",
    "Dining and Drinking > Restaurant > Steakhouse": "restaurant",
    "Dining and Drinking > Restaurant > Diner": "restaurant",
    "Dining and Drinking > Restaurant > Soup Spot": "restaurant",
    "Dining and Drinking > Restaurant > Indian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Burger Joint": "restaurant",
    "Dining and Drinking > Restaurant > Bistro": "restaurant",
    "Dining and Drinking > Restaurant > Italian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > French Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > American Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Buffet": "restaurant",
    "Dining and Drinking > Restaurant > Mexican Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Mexican Restaurant > Taco Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Mexican Restaurant > Burrito Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Salad Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Kebab Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Deli": "meal_takeaway",
    "Dining and Drinking > Restaurant > Hawaiian Restaurant > Poke Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Hawaiian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Fish and Chips Shop": "restaurant",
    "Dining and Drinking > Restaurant > Russian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Turkish Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Dumpling Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Gastropub": "restaurant",
    "Dining and Drinking > Restaurant > Middle Eastern Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Middle Eastern Restaurant > Persian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Greek Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Spanish Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Spanish Restaurant > Tapas Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Spanish Restaurant > Paella Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Comfort Food Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Gluten-Free Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Ukrainian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Mediterranean Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Australian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Caribbean Restaurant > Puerto Rican Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Caucasian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > German Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > German Restaurant > Bavarian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Eastern European Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Eastern European Restaurant > Bosnian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Moroccan Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Cajun and Creole Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Indian Chinese Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Latin American Restaurant > South American Restaurant > Argentinian Restaurant": "restaurant",
    "Dining and Drinking > Restaurant > Hot Dog Joint": "restaurant",

    # Fast/casual/quick-service -> meal_takeaway
    "Dining and Drinking > Restaurant > Fast Food Restaurant": "meal_takeaway",
    "Dining and Drinking > Food Stand": "meal_takeaway",
    "Dining and Drinking > Food Truck": "meal_takeaway",
    "Dining and Drinking > Snack Place": "meal_takeaway",

    # Food courts / cafeterias / markets
    "Dining and Drinking > Food Court": "food_court",
    "Dining and Drinking > Cafeteria": "food_court",
    "Dining and Drinking > Night Market": "market",
    "Event > Marketplace > Street Food Gathering": "market",

    # Cafe / coffee / tea
    "Dining and Drinking > Cafe, Coffee, and Tea House > Café": "cafe",
    "Dining and Drinking > Cafe, Coffee, and Tea House": "cafe",
    "Dining and Drinking > Cafe, Coffee, and Tea House > Bubble Tea Shop": "cafe",
    "Dining and Drinking > Cafe, Coffee, and Tea House > Tea Room": "cafe",
    "Dining and Drinking > Cafe, Coffee, and Tea House > Coffee Shop": "coffee_shop",
    "Retail > Food and Beverage Retail > Coffee Roaster": "coffee_shop",
    "Dining and Drinking > Juice Bar": "cafe",
    "Dining and Drinking > Smoothie Shop": "cafe",
    "Arts and Entertainment > Internet Cafe": "cafe",
    "Arts and Entertainment > Gaming Cafe": "cafe",
    "Arts and Entertainment > VR Cafe": "cafe",

    # Bakery / dessert / ice cream
    "Dining and Drinking > Bakery": "bakery",
    "Dining and Drinking > Dessert Shop > Pastry Shop": "bakery",
    "Dining and Drinking > Dessert Shop > Cupcake Shop": "bakery",
    "Dining and Drinking > Donut Shop": "bakery",
    "Dining and Drinking > Bagel Shop": "bakery",
    "Dining and Drinking > Dessert Shop": "dessert_shop",
    "Dining and Drinking > Dessert Shop > Waffle Shop": "dessert_shop",
    "Dining and Drinking > Dessert Shop > Ice Cream Parlor": "ice_cream_shop",
    "Dining and Drinking > Dessert Shop > Frozen Yogurt Shop": "ice_cream_shop",

    # Bar / nightlife -> bar
    "Dining and Drinking > Bar": "bar",
    "Dining and Drinking > Bar > Cocktail Bar": "bar",
    "Dining and Drinking > Bar > Lounge": "bar",
    "Dining and Drinking > Bar > Pub": "bar",
    "Dining and Drinking > Bar > Beer Bar": "bar",
    "Dining and Drinking > Bar > Beer Garden": "bar",
    "Dining and Drinking > Bar > Karaoke Bar": "bar",
    "Dining and Drinking > Bar > Hotel Bar": "bar",
    "Dining and Drinking > Bar > Wine Bar": "bar",
    "Dining and Drinking > Bar > Sports Bar": "bar",
    "Dining and Drinking > Bar > Speakeasy": "bar",
    "Dining and Drinking > Bar > Gay Bar": "bar",
    "Dining and Drinking > Bar > Hookah Bar": "bar",
    "Dining and Drinking > Bar > Irish Pub": "bar",
    "Dining and Drinking > Bar > Sake Bar": "bar",
    "Dining and Drinking > Bar > Piano Bar": "bar",
    "Dining and Drinking > Bar > Rooftop Bar": "bar",
    "Dining and Drinking > Bar > Beach Bar": "bar",
    "Dining and Drinking > Brewery": "bar",
    "Dining and Drinking > Winery": "bar",
    "Dining and Drinking > Cidery": "bar",
    "Arts and Entertainment > Night Club": "bar",
    "Arts and Entertainment > Salsa Club": "bar",
    "Arts and Entertainment > Dance Hall": "bar",
    "Arts and Entertainment > Performing Arts Venue > Music Venue > Jazz and Blues Venue": "bar",
    "Arts and Entertainment > Performing Arts Venue > Music Venue > Rock Club": "bar",

    # Grocery / supermarket / convenience / market
    "Retail > Convenience Store": "convenience_store",
    "Retail > Food and Beverage Retail > Beer Store": "convenience_store",
    "Retail > Food and Beverage Retail > Wine Store": "convenience_store",
    "Retail > Food and Beverage Retail > Supermarket": "supermarket",
    "Retail > Food and Beverage Retail > Grocery Store": "grocery_store",
    "Retail > Food and Beverage Retail > Grocery Store > Organic Grocery": "grocery_store",
    "Retail > Food and Beverage Retail": "grocery_store",
    "Retail > Food and Beverage Retail > Fruit and Vegetable Store": "grocery_store",
    "Retail > Food and Beverage Retail > Butcher": "grocery_store",
    "Retail > Food and Beverage Retail > Cheese Store": "grocery_store",
    "Retail > Food and Beverage Retail > Dairy Store": "grocery_store",
    "Retail > Market": "market",
    "Retail > Flea Market": "market",
    "Retail > Food and Beverage Retail > Farmers Market": "market",

    # Department stores / malls
    "Retail > Department Store": "department_store",
    "Retail > Big Box Store": "department_store",
    "Retail > Shopping Mall": "shopping_mall",

    # Pharmacy
    "Retail > Pharmacy": "pharmacy",

    # Fuel / EV charging
    "Travel and Transportation > Fuel Station": "gas_station",
    "Travel and Transportation > Electric Vehicle Charging Station": "gas_station",

    # Lodging
    "Travel and Transportation > Lodging > Hotel": "hotel",
    "Travel and Transportation > Lodging > Hotel > Hotel Pool": "hotel",
    "Travel and Transportation > Lodging > Resort": "hotel",
    "Travel and Transportation > Lodging > Hostel": "lodging",
    "Travel and Transportation > Lodging > Bed and Breakfast": "lodging",
    "Travel and Transportation > Lodging > Motel": "lodging",
    "Travel and Transportation > Lodging > Boarding House": "lodging",
    "Travel and Transportation > Lodging > Vacation Rental": "lodging",
    "Travel and Transportation > Lodging > Inn": "lodging",

    # Movie theater
    "Arts and Entertainment > Movie Theater": "movie_theater",
    "Arts and Entertainment > Movie Theater > Indie Movie Theater": "movie_theater",

    # Beauty / personal care
    "Business and Professional Services > Health and Beauty Service > Spa": "spa",
    "Business and Professional Services > Health and Beauty Service > Massage Clinic": "spa",
    "Business and Professional Services > Health and Beauty Service > Skin Care Clinic": "spa",
    "Sports and Recreation > Sauna": "spa",
    "Business and Professional Services > Health and Beauty Service > Hair Salon": "hair_salon",
    "Business and Professional Services > Health and Beauty Service > Nail Salon": "nail_salon",
    "Business and Professional Services > Health and Beauty Service > Barbershop": "barber_shop",
    "Business and Professional Services > Health and Beauty Service": "beauty_salon",
    "Business and Professional Services > Health and Beauty Service > Tattoo Parlor": "beauty_salon",
    "Business and Professional Services > Health and Beauty Service > Hair Removal Service": "beauty_salon",
    "Business and Professional Services > Laundry Service": "laundry",
    "Business and Professional Services > Laundromat": "laundry",
    "Business and Professional Services > Health and Beauty Service > Dry Cleaner": "laundry",

    # Gym / fitness / sports & recreation
    "Sports and Recreation > Gym and Studio > Gym": "gym",
    "Sports and Recreation > Gym and Studio": "gym",
    "Sports and Recreation > Gym and Studio > Yoga Studio": "gym",
    "Sports and Recreation > Gym and Studio > Pilates Studio": "gym",
    "Sports and Recreation > Gym and Studio > Gym Pool": "gym",
    "Sports and Recreation > Sports Club": "gym",
    "Sports and Recreation > Racquet Sports": "gym",
    "Sports and Recreation > Racquet Sports > Tennis > Tennis Court": "gym",
    "Sports and Recreation > Racquet Sports > Racquet Sport Club": "gym",
    "Sports and Recreation > Volleyball Court": "gym",
    "Sports and Recreation > Basketball > Basketball Court": "gym",
    "Sports and Recreation > Football > Football Field": "gym",
    "Sports and Recreation > Soccer > Soccer Field": "gym",
    "Sports and Recreation > Water Sports > Swimming > Swimming Pool": "gym",
    "Sports and Recreation > Water Sports > Surfing": "gym",
    "Sports and Recreation > Martial Arts Dojo": "gym",
    "Sports and Recreation > Indoor Play Area": "gym",
    "Sports and Recreation": "gym",
    "Community and Government > Education > College and University > College Gym": "gym",

    # --- Generic retail "store" (specialty shops with no dedicated target) ---
    "Retail > Fashion Retail > Clothing Store": "store",
    "Retail > Fashion Retail > Shoe Store": "store",
    "Retail > Fashion Retail > Men's Store": "store",
    "Retail > Fashion Retail > Women's Store": "store",
    "Retail > Fashion Retail > Jewelry Store": "store",
    "Retail > Fashion Retail > Bridal Store": "store",
    "Retail > Fashion Retail > Fashion Accessories Store": "store",
    "Retail > Fashion Retail > Children's Clothing Store": "store",
    "Retail > Fashion Retail > Lingerie Store": "store",
    "Retail > Fashion Retail": "store",
    "Retail > Cosmetics Store": "store",
    "Retail > Sporting Goods Retail": "store",
    "Retail > Sporting Goods Retail > Dive Store": "store",
    "Retail > Sporting Goods Retail > Bicycle Store": "store",
    "Retail > Gift Store": "store",
    "Retail > Souvenir Store": "store",
    "Retail > Vintage and Thrift Store": "store",
    "Retail > Computers and Electronics Retail > Electronics Store": "store",
    "Retail > Computers and Electronics Retail > Mobile Phone Store": "store",
    "Retail > Computers and Electronics Retail > Video Games Store": "store",
    "Retail > Bookstore": "store",
    "Retail > Bookstore > Used Bookstore": "store",
    "Retail > Baby Store": "store",
    "Retail > Arts and Crafts Store": "store",
    "Retail > Office Supply Store": "store",
    "Retail > Betting Shop": "store",
    "Retail > Smoke Shop": "store",
    "Retail > Miscellaneous Store": "store",
    "Retail > Toy Store": "store",
    "Retail > Flower Store": "store",
    "Retail > Outdoor Supply Store": "store",
    "Retail > Eyecare Store": "store",
    "Retail > Food and Beverage Retail > Chocolate Store": "store",
    "Retail > Tobacco Store": "store",
    "Retail > Board Store": "store",
    "Retail > Video Store": "store",
    "Retail > Print Store": "store",
    "Retail > Newsstand": "store",
    "Retail > Costume Store": "store",
    "Retail > Pet Supplies Store": "store",
    "Retail > Hardware Store": "store",
    "Retail > Perfume Store": "store",
    "Retail > Boutique": "store",
    "Retail > Supplement Store": "store",
    "Retail > Automotive Retail > Motorcycle Dealership": "store",
    "Retail > Record Store": "store",

    # --- Everything else: no matching target category exists, so this is
    # forced into FALLBACK_CATEGORY. Kept as explicit entries (rather than
    # relying purely on the fallback branch) so the mapping stays auditable. ---
    "Business and Professional Services > Office": FALLBACK_CATEGORY,
    "Business and Professional Services > Office > Coworking Space": FALLBACK_CATEGORY,
    "Business and Professional Services > Office > Tech Startup": FALLBACK_CATEGORY,
    "Business and Professional Services > Office > Meeting Room": FALLBACK_CATEGORY,
    "Business and Professional Services > Office > Campaign Office": FALLBACK_CATEGORY,
    "Business and Professional Services > Office > Office Building": FALLBACK_CATEGORY,
    "Business and Professional Services > Event Space": FALLBACK_CATEGORY,
    "Business and Professional Services > Financial Service > Banking and Finance > Bank": FALLBACK_CATEGORY,
    "Business and Professional Services > Financial Service > Banking and Finance > ATM": FALLBACK_CATEGORY,
    "Business and Professional Services > Financial Service > Currency Exchange": FALLBACK_CATEGORY,
    "Business and Professional Services > Financial Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Real Estate Service > Real Estate Agency": FALLBACK_CATEGORY,
    "Business and Professional Services > Automotive Service > Car Wash and Detail": FALLBACK_CATEGORY,
    "Business and Professional Services > Automotive Service > Automotive Repair Shop": FALLBACK_CATEGORY,
    "Business and Professional Services > Shoe Repair Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Tailor": FALLBACK_CATEGORY,
    "Business and Professional Services > Rental Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Technology Business > IT Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Ballroom": FALLBACK_CATEGORY,
    "Business and Professional Services > Funeral Home": FALLBACK_CATEGORY,
    "Business and Professional Services > Pet Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Photography Service > Photography Studio": FALLBACK_CATEGORY,
    "Business and Professional Services > Photography Service > Photography Lab": FALLBACK_CATEGORY,
    "Business and Professional Services > Business Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Design Studio": FALLBACK_CATEGORY,
    "Business and Professional Services > Advertising Agency": FALLBACK_CATEGORY,
    "Business and Professional Services > Distribution Center": FALLBACK_CATEGORY,
    "Business and Professional Services > Business Center": FALLBACK_CATEGORY,
    "Business and Professional Services > Home Improvement Service > Home Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Insurance Agency": FALLBACK_CATEGORY,
    "Business and Professional Services > Legal Service": FALLBACK_CATEGORY,
    "Business and Professional Services > Convention Center": FALLBACK_CATEGORY,
    "Business and Professional Services > Convention Center > Conference Room": FALLBACK_CATEGORY,
    "Business and Professional Services": FALLBACK_CATEGORY,

    "Community and Government > Residential Building > Apartment or Condo": FALLBACK_CATEGORY,
    "Community and Government > Residential Building": FALLBACK_CATEGORY,
    "Community and Government > Government Building": FALLBACK_CATEGORY,
    "Community and Government > Government Building > Post Office": FALLBACK_CATEGORY,
    "Community and Government > Government Building > Military > Military Base": FALLBACK_CATEGORY,
    "Community and Government > Government Building > Law Enforcement and Public Safety > Police Station": FALLBACK_CATEGORY,
    "Community and Government > Government Building > City Hall": FALLBACK_CATEGORY,
    "Community and Government > Government Building > Embassy or Consulate": FALLBACK_CATEGORY,
    "Community and Government > Government Building > Capitol Building": FALLBACK_CATEGORY,
    "Community and Government > Spiritual Center > Church": FALLBACK_CATEGORY,
    "Community and Government > Spiritual Center > Buddhist Temple": FALLBACK_CATEGORY,
    "Community and Government > Spiritual Center > Temple": FALLBACK_CATEGORY,
    "Community and Government > Education": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > University": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > Student Center": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Academic Building": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > Community College": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Technology Building": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Classroom": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Library": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Residence Hall": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Administrative Building": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Communications Building": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Auditorium": FALLBACK_CATEGORY,
    "Community and Government > Education > College and University > College Quad": FALLBACK_CATEGORY,
    "Community and Government > Education > Primary and Secondary School > High School": FALLBACK_CATEGORY,
    "Community and Government > Education > Primary and Secondary School > Elementary School": FALLBACK_CATEGORY,
    "Community and Government > Education > Nursery School": FALLBACK_CATEGORY,
    "Community and Government > Education > Preschool": FALLBACK_CATEGORY,
    "Community and Government > Education > Adult Education": FALLBACK_CATEGORY,
    "Community and Government > Education > Trade School": FALLBACK_CATEGORY,
    "Community and Government > Education > Language School": FALLBACK_CATEGORY,
    "Community and Government > Education > Music School": FALLBACK_CATEGORY,
    "Community and Government > Library": FALLBACK_CATEGORY,
    "Community and Government > Housing Development": FALLBACK_CATEGORY,
    "Community and Government > Organization > Club House": FALLBACK_CATEGORY,
    "Community and Government > Cultural Center": FALLBACK_CATEGORY,
    "Community and Government > Animal Shelter": FALLBACK_CATEGORY,
    "Community and Government > Assisted Living": FALLBACK_CATEGORY,

    "Health and Medicine > Hospital": FALLBACK_CATEGORY,
    "Health and Medicine > Medical Center": FALLBACK_CATEGORY,
    "Health and Medicine > Physician > Doctor's Office": FALLBACK_CATEGORY,
    "Health and Medicine > Physician > Dermatologist": FALLBACK_CATEGORY,
    "Health and Medicine > Dentist": FALLBACK_CATEGORY,
    "Health and Medicine > Veterinarian": FALLBACK_CATEGORY,
    "Health and Medicine > Optometrist": FALLBACK_CATEGORY,

    "Landmarks and Outdoors > Structure": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Beach": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Bridge": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > States and Municipalities > Neighborhood": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Harbor or Marina": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Roof Deck": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Waterfront": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Garden": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Park": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Park > Playground": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Scenic Lookout": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Surf Spot": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Historic and Protected Site": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Bay": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Farm": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > River": FALLBACK_CATEGORY,
    "Landmarks and Outdoors > Plaza": FALLBACK_CATEGORY,

    "Travel and Transportation": FALLBACK_CATEGORY,
    "Travel and Transportation > Road": FALLBACK_CATEGORY,
    "Travel and Transportation > Travel Agency": FALLBACK_CATEGORY,
    "Travel and Transportation > Bike Rental": FALLBACK_CATEGORY,
    "Travel and Transportation > Transport Hub > Bus Stop": FALLBACK_CATEGORY,
    "Travel and Transportation > Transport Hub > Rental Car Location": FALLBACK_CATEGORY,
    "Travel and Transportation > Transportation Service > Public Transportation > Bus Line": FALLBACK_CATEGORY,
    "Travel and Transportation > Transportation Service": FALLBACK_CATEGORY,
    "Travel and Transportation > Travel Lounge": FALLBACK_CATEGORY,
    "Travel and Transportation > Cruise": FALLBACK_CATEGORY,
    "Travel and Transportation > Boat or Ferry": FALLBACK_CATEGORY,
    "Travel and Transportation > Pier": FALLBACK_CATEGORY,
    "Travel and Transportation > Tourist Information and Service": FALLBACK_CATEGORY,

    "Arts and Entertainment": FALLBACK_CATEGORY,
    "Arts and Entertainment > Pool Hall": FALLBACK_CATEGORY,
    "Arts and Entertainment > Performing Arts Venue > Music Venue": FALLBACK_CATEGORY,
    "Arts and Entertainment > Performing Arts Venue > Concert Hall": FALLBACK_CATEGORY,
    "Arts and Entertainment > Performing Arts Venue": FALLBACK_CATEGORY,
    "Arts and Entertainment > Performing Arts Venue > Amphitheater": FALLBACK_CATEGORY,
    "Arts and Entertainment > Stadium > Football Stadium": FALLBACK_CATEGORY,
    "Arts and Entertainment > Stadium": FALLBACK_CATEGORY,
    "Arts and Entertainment > Art Gallery": FALLBACK_CATEGORY,
    "Arts and Entertainment > Museum": FALLBACK_CATEGORY,
    "Arts and Entertainment > Museum > History Museum": FALLBACK_CATEGORY,
    "Arts and Entertainment > Museum > Art Museum": FALLBACK_CATEGORY,
    "Arts and Entertainment > Casino": FALLBACK_CATEGORY,
    "Arts and Entertainment > Circus": FALLBACK_CATEGORY,
    "Arts and Entertainment > Bowling Alley": FALLBACK_CATEGORY,
    "Arts and Entertainment > Arcade": FALLBACK_CATEGORY,
    "Arts and Entertainment > Amusement Park": FALLBACK_CATEGORY,
    "Arts and Entertainment > Amusement Park > Attraction": FALLBACK_CATEGORY,
}


def parse_label_list(raw):
    """Parse a numpy-array-style repr like "['A'\n 'B']" into a list of str."""
    raw = (raw or "").strip()
    if not raw:
        return []
    return _LABEL_RE.findall(raw)


def normalize(labels, unmapped_counter):
    mapped = []
    for label in labels:
        target = CATEGORY_MAP.get(label)
        if target is None:
            unmapped_counter[label] = unmapped_counter.get(label, 0) + 1
            target = FALLBACK_CATEGORY
        if target not in mapped:
            mapped.append(target)
    return mapped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument(
        "--no-backup", action="store_true",
        help="skip writing a .bak copy of the original file",
    )
    args = parser.parse_args()

    csv_path: Path = args.csv_path
    if not csv_path.exists():
        sys.exit(f"File not found: {csv_path}")

    if not args.no_backup:
        backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
        shutil.copyfile(csv_path, backup_path)
        print(f"Backup written to {backup_path}")

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    col_idx = header.index("fsq_category_labels")

    unmapped_counter = {}
    changed = 0
    for row in rows[1:]:
        if col_idx >= len(row):
            continue
        original_labels = parse_label_list(row[col_idx])
        new_labels = normalize(original_labels, unmapped_counter)
        new_value = repr(new_labels)
        if new_value != row[col_idx]:
            changed += 1
        row[col_idx] = new_value

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Rewrote {changed} of {len(rows) - 1} data rows in {csv_path}")

    if unmapped_counter:
        print(
            f"\n{len(unmapped_counter)} distinct label(s) had no explicit entry "
            f"in CATEGORY_MAP and were forced to '{FALLBACK_CATEGORY}':"
        )
        for label, count in sorted(unmapped_counter.items(), key=lambda kv: -kv[1]):
            print(f"  {count:5d}  {label}")
    else:
        print("Every label in the file had an explicit CATEGORY_MAP entry.")


if __name__ == "__main__":
    main()
