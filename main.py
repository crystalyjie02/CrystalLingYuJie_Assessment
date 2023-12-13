import os
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.hash import bcrypt
from passlib.context import CryptContext
from dotenv import load_dotenv
from databases import Database
from sqlalchemy import create_engine, Column, String, Boolean, MetaData, Table, Integer

load_dotenv() #Load environment variables from .env file

SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
DATABASE_URL = os.environ.get("DATABASE_URL")

# Database configuration
DATABASE_URL = (
    f"mysql://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}"
    f"@{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}/{os.environ['DATABASE']}"
)

database = Database(DATABASE_URL)

# Create a metadata object
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, nullable=False),
    Column("hashed_password", String),
    Column("disabled", Boolean, default=False, nullable=True),
)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str or None = None

class TokenResponse(BaseModel):
    username: str
    access_token: str

class User(BaseModel):
    username: str
    full_name: str or None = None
    email: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_db_client():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await database.disconnect()

async def create_user(db, username: str, password: str):
    hashed_password = pwd_context.hash(password)
    query = users.insert().values(
        username=username,
        hashed_password=hashed_password,
        disabled=False
    )
    return await db.execute(query)

async def get_user_by_username(db, username: str):
    query = users.select().where(users.c.username == username)
    user_row = await db.fetch_one(query)
    
    if user_row:
        user = dict(user_row)
        user['hashed_password'] = str(user['hashed_password'])  # Ensure it's a string
        return user
    return None

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": encoded_jwt, "token_type": "bearer"}

@app.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await get_user_by_username(database, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    return {"username": form_data.username, "access_token": access_token["access_token"]}

@app.get("/register")
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await get_user_by_username(database, username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    await create_user(database, username, password)
    return templates.TemplateResponse("registration_success.html", {"request": request, "username": username})

@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
