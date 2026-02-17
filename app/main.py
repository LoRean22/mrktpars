from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
from core.browser_manager import browser_manager



from api import users
from core.http_client import init_http_session, close_http_session

app = FastAPI()

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Startup / Shutdown
# ----------------------------
@app.on_event("startup")
async def startup():
    await init_http_session()
    await browser_manager.start()


@app.on_event("shutdown")
async def shutdown():
    await browser_manager.stop()
    await close_http_session()


# ----------------------------
# Routers
# ----------------------------
app.include_router(users.router)

@app.get("/")
def root():
    return {"status": "MRKTPARS backend running"}
