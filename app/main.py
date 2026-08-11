from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import Base, engine
from .routers import customer, admin

app = FastAPI(title="Wardrobe & Co. Furniture Showroom")

# Create tables if they do not already exist (schema.sql can also be run manually)
Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(customer.router)
app.include_router(admin.router)


@app.exception_handler(HTTPException)
async def redirect_on_auth_exception(request: Request, exc: HTTPException):
    # Dependencies raise a 303 + Location header when login is required;
    # translate that into an actual redirect instead of a JSON error.
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code,
    )
