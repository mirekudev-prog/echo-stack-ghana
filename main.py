from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="EchoStack API")

# Allow CORS (so frontend can talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to EchoStack - Ghana's Heritage Archive"}

@app.get("/api/regions")
def get_regions():
    return [
        {"id": 1, "name": "Ashanti", "description": "The heart of the Ashanti Kingdom..."},
        {"id": 2, "name": "Eastern", "description": "Sixth largest region by area..."},
        {"id": 3, "name": "Savannah", "description": "Ghana's largest region by land..."},
        {"id": 4, "name": "North East", "description": "Northern Ghana with diverse landscapes..."},
    ]
