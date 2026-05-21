from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, chat, challenges, users
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.DEBUG)
load_dotenv()

app = FastAPI(
    title="SnapQuest API",
    description="API pour l'application mobile SnapQuest",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # fixed: can't use True with allow_origins=["*"] — invalid CORS combo.
    allow_methods=["*"],      # Auth uses Authorization header (not cookies) so False is correct.
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(challenges.router, prefix="/challenges", tags=["Challenges"])
app.include_router(users.router, prefix="/users", tags=["Users"])


@app.get("/")
def root():
    return {"message": "SnapQuest API 🗺️"}