import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# ---------------------- E-COMMERCE ENDPOINTS ----------------------

class CreateProduct(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image: Optional[str] = None
    rating: Optional[float] = None


def _serialize(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Ensure types are JSON friendly
    return d

@app.get("/api/products")
async def list_products(
    search: Optional[str] = Query(None, description="Search query for title or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(48, ge=1, le=200)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filt = {}
    if search:
        filt["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    if category:
        filt["category"] = category

    docs = get_documents("product", filt, limit)
    return {"items": [_serialize(d) for d in docs]}

@app.get("/api/categories")
async def get_categories():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Distinct categories from products
    cats = db["product"].distinct("category")
    return {"items": sorted([c for c in cats if c])}

@app.post("/api/products")
async def create_product(payload: CreateProduct):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Validate with Pydantic schema for consistency
    p = ProductSchema(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        in_stock=payload.in_stock,
    )
    new_id = create_document("product", {**p.model_dump(), "image": payload.image, "rating": payload.rating})
    doc = db["product"].find_one({"_id": db["product"].database.client.get_default_database()["product"].database.client.get_default_database()})
    # Fallback to fetch by id string when above isn't available in this environment
    try:
        from bson import ObjectId
        created = db["product"].find_one({"_id": ObjectId(new_id)})
    except Exception:
        created = db["product"].find_one(sort=[("_id", -1)])
    return {"item": _serialize(created)}

@app.post("/api/seed")
async def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    count = db["product"].count_documents({})
    if count > 0:
        return {"status": "ok", "message": "Products already exist", "count": count}

    sample = [
        {
            "title": "Apple iPhone 15",
            "description": "Dynamic Island, A16 Bionic, 6.1-inch Super Retina XDR",
            "price": 799.0,
            "category": "Mobiles",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1695048133142-93b2b88a93df?w=800",
            "rating": 4.6,
        },
        {
            "title": "Samsung Galaxy S23",
            "description": "Snapdragon 8 Gen 2, Pro-grade camera",
            "price": 699.0,
            "category": "Mobiles",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1675866231057-1c5efb395c3b?w=800",
            "rating": 4.5,
        },
        {
            "title": "Sony WH-1000XM5",
            "description": "Industry leading noise canceling headphones",
            "price": 349.0,
            "category": "Audio",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=800",
            "rating": 4.7,
        },
        {
            "title": "HP Victus Gaming Laptop",
            "description": "Ryzen 7, RTX 4060, 16GB RAM, 512GB SSD",
            "price": 1199.0,
            "category": "Laptops",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800",
            "rating": 4.3,
        },
        {
            "title": "Nike Air Max",
            "description": "Breathable mesh, all-day comfort",
            "price": 129.0,
            "category": "Fashion",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800",
            "rating": 4.4,
        },
        {
            "title": "Canon EOS R10",
            "description": "Mirrorless camera with 24.2MP sensor",
            "price": 999.0,
            "category": "Cameras",
            "in_stock": True,
            "image": "https://images.unsplash.com/photo-1519183071298-a2962be96f83?w=800",
            "rating": 4.5,
        },
    ]

    for s in sample:
        create_document("product", s)

    new_count = db["product"].count_documents({})
    return {"status": "ok", "inserted": len(sample), "count": new_count}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
