from pymongo import ASCENDING, MongoClient

from app.core.config import settings


client = MongoClient(settings.mongodb_uri)
database = client[settings.mongodb_db]

owners_collection = database["owners"]
shops_collection = database["shops"]
products_collection = database["products"]
categories_collection = database["categories"]


def create_indexes() -> None:
    owners_collection.create_index([("email", ASCENDING)], unique=True)
    shops_collection.create_index([("owner_id", ASCENDING)])
    products_collection.create_index([("owner_id", ASCENDING), ("shop_id", ASCENDING)])
    categories_collection.create_index(
        [("owner_id", ASCENDING), ("shop_id", ASCENDING), ("name", ASCENDING)],
        unique=True,
    )
