from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def admin_or_redirect(request: Request, db: Session):
    user = auth.get_current_user(request, db)
    if not user or user.role != "admin":
        return None
    return user


@router.get("/login")
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@router.post("/login")
def admin_login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                        db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email, models.User.role == "admin").first()
    if not user or not auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "error": "Incorrect admin credentials."})
    token = auth.create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=3600 * 2)
    return response


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    product_count = db.query(func.count(models.Product.id)).scalar()
    order_count = db.query(func.count(models.Order.id)).scalar()
    revenue = db.query(func.coalesce(func.sum(models.Order.total_amount), 0)).filter(
        models.Order.status != "cancelled").scalar()
    low_stock = db.query(models.Product).filter(models.Product.stock_quantity <= 5).order_by(
        models.Product.stock_quantity).limit(5).all()
    recent_orders = db.query(models.Order).order_by(models.Order.created_at.desc()).limit(5).all()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user, "product_count": product_count,
        "order_count": order_count, "revenue": revenue, "low_stock": low_stock,
        "recent_orders": recent_orders,
    })


# ---------- Products ----------
@router.get("/products")
def list_products(request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    products = db.query(models.Product).order_by(models.Product.id.desc()).all()
    return templates.TemplateResponse("admin/products.html", {"request": request, "user": user, "products": products})


@router.get("/products/new")
def new_product_page(request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse("admin/product_form.html", {
        "request": request, "user": user, "categories": categories, "product": None})


@router.post("/products/new")
def create_product(request: Request, name: str = Form(...), description: str = Form(""),
                    price: float = Form(...), stock_quantity: int = Form(0),
                    material: str = Form(""), dimensions: str = Form(""),
                    image_url: str = Form(""), category_id: int = Form(...),
                    db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    product = models.Product(name=name, description=description, price=price,
                              stock_quantity=stock_quantity, material=material,
                              dimensions=dimensions, image_url=image_url,
                              category_id=category_id or None)
    db.add(product)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


@router.get("/products/{product_id}/edit")
def edit_product_page(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse("admin/product_form.html", {
        "request": request, "user": user, "categories": categories, "product": product})


@router.post("/products/{product_id}/edit")
def update_product(product_id: int, request: Request, name: str = Form(...),
                    description: str = Form(""), price: float = Form(...),
                    stock_quantity: int = Form(0), material: str = Form(""),
                    dimensions: str = Form(""), image_url: str = Form(""),
                    category_id: int = Form(...), is_active: bool = Form(False),
                    db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.name = name
    product.description = description
    product.price = price
    product.stock_quantity = stock_quantity
    product.material = material
    product.dimensions = dimensions
    product.image_url = image_url
    product.category_id = category_id or None
    product.is_active = is_active
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


@router.post("/products/{product_id}/delete")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


# ---------- Categories ----------
@router.get("/categories")
def list_categories(request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse("admin/categories.html", {"request": request, "user": user, "categories": categories})


@router.post("/categories/new")
def create_category(request: Request, name: str = Form(...), description: str = Form(""),
                     db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    db.add(models.Category(name=name, description=description))
    db.commit()
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if category:
        db.delete(category)
        db.commit()
    return RedirectResponse(url="/admin/categories", status_code=303)


# ---------- Orders ----------
@router.get("/orders")
def list_orders(request: Request, db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    return templates.TemplateResponse("admin/orders.html", {"request": request, "user": user, "orders": orders})


@router.post("/orders/{order_id}/status")
def update_order_status(order_id: int, request: Request, status: str = Form(...),
                         db: Session = Depends(get_db)):
    user = admin_or_redirect(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=303)
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order and status in ("pending", "confirmed", "shipped", "delivered", "cancelled"):
        order.status = status
        db.commit()
    return RedirectResponse(url="/admin/orders", status_code=303)
