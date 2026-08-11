from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from .. import models, auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ---------- Catalog ----------
@router.get("/")
def catalog(request: Request, q: str = "", category: int = 0, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    query = db.query(models.Product).filter(models.Product.is_active == True)
    if q:
        query = query.filter(or_(models.Product.name.ilike(f"%{q}%"),
                                  models.Product.description.ilike(f"%{q}%")))
    if category:
        query = query.filter(models.Product.category_id == category)
    products = query.order_by(models.Product.created_at.desc()).all()
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse("index.html", {
        "request": request, "user": user, "products": products,
        "categories": categories, "q": q, "selected_category": category,
    })


@router.get("/product/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse("product_detail.html", {
        "request": request, "user": user, "product": product,
    })


# ---------- Auth ----------
@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": None})


@router.post("/register")
def register_submit(request: Request, full_name: str = Form(...), email: str = Form(...),
                     password: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request, "user": None, "error": "An account with that email already exists."})
    new_user = models.User(full_name=full_name, email=email,
                            password_hash=auth.hash_password(password), role="customer")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = auth.create_access_token({"sub": str(new_user.id)})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=3600 * 2)
    return response


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})


@router.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                  db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, "user": None, "error": "Incorrect email or password."})
    token = auth.create_access_token({"sub": str(user.id)})
    redirect_to = "/admin" if user.role == "admin" else "/"
    response = RedirectResponse(url=redirect_to, status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=3600 * 2)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


# ---------- Cart ----------
@router.get("/cart")
def view_cart(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    total = sum(float(i.product.price) * i.quantity for i in items)
    return templates.TemplateResponse("cart.html", {
        "request": request, "user": user, "items": items, "total": total,
    })


@router.post("/cart/add/{product_id}")
def add_to_cart(product_id: int, request: Request, quantity: int = Form(1),
                 db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user.id, models.CartItem.product_id == product_id).first()
    if item:
        item.quantity += quantity
    else:
        item = models.CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
        db.add(item)
    db.commit()
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/update/{item_id}")
def update_cart_item(item_id: int, request: Request, quantity: int = Form(...),
                      db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id, models.CartItem.user_id == user.id).first()
    if item:
        if quantity <= 0:
            db.delete(item)
        else:
            item.quantity = quantity
        db.commit()
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/remove/{item_id}")
def remove_cart_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id, models.CartItem.user_id == user.id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/cart", status_code=303)


# ---------- Checkout & Orders ----------
@router.get("/checkout")
def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    if not items:
        return RedirectResponse(url="/cart", status_code=303)
    total = sum(float(i.product.price) * i.quantity for i in items)
    return templates.TemplateResponse("checkout.html", {
        "request": request, "user": user, "items": items, "total": total,
    })


@router.post("/checkout")
def place_order(request: Request, shipping_address: str = Form(...), db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    if not items:
        return RedirectResponse(url="/cart", status_code=303)

    total = sum(float(i.product.price) * i.quantity for i in items)
    order = models.Order(user_id=user.id, total_amount=total,
                          shipping_address=shipping_address, status="pending")
    db.add(order)
    db.flush()

    for i in items:
        db.add(models.OrderItem(order_id=order.id, product_id=i.product_id,
                                 quantity=i.quantity, price_at_purchase=i.product.price))
        if i.product.stock_quantity >= i.quantity:
            i.product.stock_quantity -= i.quantity
        db.delete(i)

    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


@router.get("/orders")
def order_history(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    orders = db.query(models.Order).filter(models.Order.user_id == user.id).order_by(
        models.Order.created_at.desc()).all()
    return templates.TemplateResponse("orders.html", {"request": request, "user": user, "orders": orders})


@router.get("/orders/{order_id}")
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse("order_detail.html", {"request": request, "user": user, "order": order})
