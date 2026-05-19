from pymongo import ASCENDING, MongoClient

from app.core.config import settings


client = MongoClient(settings.mongodb_uri)
database = client[settings.mongodb_db]

owners_collection = database["owners"]
shops_collection = database["shops"]
products_collection = database["products"]
categories_collection = database["categories"]
orders_collection = database["orders"]
chat_sessions_collection = database["chat_sessions"]
owner_conversations_collection = database["owner_conversations"]
owner_conversation_messages_collection = database["owner_conversation_messages"]


def create_indexes() -> None:
    owners_collection.create_index([("email", ASCENDING)], unique=True)
    shops_collection.create_index([("owner_id", ASCENDING)])
    products_collection.create_index([("owner_id", ASCENDING), ("shop_id", ASCENDING)])
    orders_collection.create_index([("shop_id", ASCENDING)])
    orders_collection.create_index([("session_id", ASCENDING)])
    chat_sessions_collection.create_index([("session_id", ASCENDING), ("shop_id", ASCENDING)], unique=True)
    categories_collection.create_index(
        [("owner_id", ASCENDING), ("shop_id", ASCENDING), ("name", ASCENDING)],
        unique=True,
    )
    owner_conversations_collection.create_index([("owner_id", ASCENDING)])
    owner_conversation_messages_collection.create_index([("conversation_id", ASCENDING)])
