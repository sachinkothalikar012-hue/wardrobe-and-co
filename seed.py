"""
Run once after creating the database to add a default admin account
and a few sample products, so the app isn't empty on first launch.

Usage:
    python seed.py
"""
from app.database import SessionLocal, Base, engine
from app import models
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- Admin account ---
if not db.query(models.User).filter(models.User.email == "admin@showroom.com").first():
    db.add(models.User(
        full_name="Showroom Admin",
        email="admin@showroom.com",
        password_hash=hash_password("Admin@123"),
        role="admin",
    ))
    print("Created admin account -> admin@showroom.com / Admin@123")

# --- Sample categories ---
category_names = ["Sofas", "Tables", "Chairs", "Beds", "Storage"]
categories = {}
for name in category_names:
    cat = db.query(models.Category).filter(models.Category.name == name).first()
    if not cat:
        cat = models.Category(name=name, description=f"{name} for every room")
        db.add(cat)
        db.flush()
    categories[name] = cat

db.commit()

# --- Sample products ---
sample_products = [
    ("Camden Three-Seat Sofa", "Sofas", 899.00, 12, "Linen upholstery, oak legs", "210 x 90 x 85 cm",
     "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=600"),
    ("Alder Oak Dining Table", "Tables", 649.00, 8, "Solid oak", "180 x 90 x 76 cm",
     "https://images.unsplash.com/photo-1615874959474-d609969a20ed?w=600"),
    ("Marlow Accent Chair", "Chairs", 279.00, 20, "Velvet, walnut frame", "70 x 75 x 80 cm",
     "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=600"),
    ("Hollis Upholstered Bed Frame", "Beds", 549.00, 6, "Boucle fabric, pine frame", "Queen, 160 x 200 cm",
     "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=600"),
    ("Nordby 3-Door Wardrobe", "Storage", 469.00, 5, "Engineered wood", "120 x 55 x 200 cm",
     "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=600"),
    ("Birchwood Coffee Table", "Tables", 219.00, 15, "Birch veneer", "110 x 55 x 45 cm",
     "https://images.unsplash.com/photo-1499933374294-4584851497cc?w=600"),
]

for name, cat_name, price, stock, material, dims, img in sample_products:
    if not db.query(models.Product).filter(models.Product.name == name).first():
        db.add(models.Product(
            name=name, description=f"{name} — a showroom favorite crafted for everyday living.",
            price=price, stock_quantity=stock, material=material, dimensions=dims,
            image_url=img, category_id=categories[cat_name].id,
        ))

db.commit()
db.close()
print("Seed complete.")
