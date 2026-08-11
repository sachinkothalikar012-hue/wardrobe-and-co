# Wardrobe & Co. — Furniture Showroom System

A full-stack furniture showroom app: customers browse and buy, admins manage
inventory and orders. Built with **FastAPI**, **MySQL** (via SQLAlchemy), and
server-rendered **HTML/CSS** (Jinja2 templates).

## Features

**Customer side**
- Browse the catalog, filter by category, search by name/description
- Product detail pages with price, material, dimensions, stock
- Account registration/login (JWT stored in an HTTP-only cookie)
- Cart: add, update quantity, remove
- Checkout with shipping address → creates an order, reduces stock
- Order history and order detail pages

**Admin side** (role = `admin`)
- Separate admin login at `/admin/login`
- Dashboard: product/order counts, revenue, low-stock alert, recent orders
- Products: create, edit, delete, toggle visibility
- Categories: create, delete
- Orders: view all orders, update status (pending → confirmed → shipped → delivered/cancelled)

## Project structure

```
furniture_showroom/
├── app/
│   ├── main.py            # FastAPI app, routing, startup
│   ├── database.py        # SQLAlchemy engine/session
│   ├── models.py          # ORM models (User, Category, Product, Cart, Order...)
│   ├── auth.py            # password hashing + JWT cookie auth
│   ├── routers/
│   │   ├── customer.py    # catalog, auth, cart, checkout, orders
│   │   └── admin.py       # admin dashboard, product/category/order CRUD
│   ├── templates/         # Jinja2 HTML templates
│   └── static/css/style.css
├── schema.sql              # MySQL schema (run manually, or let SQLAlchemy create it)
├── seed.py                  # creates admin account + sample products
├── requirements.txt
└── .env.example
```

## Setup

1. **Create the database** (MySQL must be running):
   ```bash
   mysql -u root -p < schema.sql
   ```
   This creates the `furniture_showroom` database, tables, and 5 starter categories.
   (Skipping this is fine too — `app/main.py` auto-creates tables on first run,
   but you still need the database itself to exist: `CREATE DATABASE furniture_showroom;`)

2. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**: copy `.env.example` to `.env` and set your real
   MySQL credentials and a random `SECRET_KEY`:
   ```bash
   cp .env.example .env
   ```

4. **Seed an admin account and sample products**:
   ```bash
   python seed.py
   ```
   Creates `admin@showroom.com` / `Admin@123` — **change this password after first login.**

5. **Run the app**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Visit `http://127.0.0.1:8000` for the showroom, `http://127.0.0.1:8000/admin/login` for admin.

## Notes on how auth works

Login issues a JWT signed with `SECRET_KEY`, stored in an `access_token`
HTTP-only cookie. `auth.get_current_user` reads and validates it on every
request. Customer routes redirect to `/login`; admin routes redirect to
`/admin/login` if the user isn't an authenticated admin. Passwords are hashed
with bcrypt via `passlib` — never stored in plain text.

## Extending it

- Swap the placeholder Unsplash image URLs for uploaded product photos
  (add a file-upload field + static serving).
- Add pagination to `/` once the catalog grows past a page or two.
- Add email confirmation for orders (e.g. via a background task).
- Wrap the checkout total calculation in a DB transaction with row locking
  if you expect concurrent orders on low-stock items.
