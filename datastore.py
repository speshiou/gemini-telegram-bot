from datetime import datetime
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import config

class Datastore:
    def __init__(self):
        uri: str = f"mongodb://mongo:{config.MONGODB_PORT}"
        self.client: MongoClient = MongoClient(uri)
        self.db: Database = self.client[config.MONGODB_NAME]
        # collections
        self.chat_collection: Collection = self.db["chats"]

    def upsert_chat(self, chat_id: int) -> None:
        default_data = {
            "first_interaction": datetime.utcnow(),
            "history": [],
        }

        data = {
            "last_interaction": datetime.utcnow(),
        }

        filter = {
            "_id": chat_id
        }

        update = {
            "$set": data,
            "$setOnInsert": default_data,
        }

        self.chat_collection.update_one(filter, update, upsert=True)

    def get_chat_history(self, chat_id: int):
        filter = {
            "_id": chat_id
        }

        doc = self.chat_collection.find_one(filter)
        return doc["history"] if doc else []
    
    def push_chat_history(self, chat_id: int, user_message: str, model_message: str, trim_history: int = 0):
        filter = {
            "_id": chat_id
        }

        new_messages = {
            "user": user_message,
            "model": model_message,
        }

        if trim_history > 0:
            self.chat_collection.update_one(
                filter,
                {
                    "$push": {
                        "history": {
                            "$each": [ new_messages ],
                            "$slice": -trim_history,
                        }
                    }
                }
            )
        else:
            self.chat_collection.update_one(
                filter,
                {
                    "$push": {
                        "history": new_messages
                    }
                }
            )

    def clear_chat_history(self, chat_id: int):
        filter = {
            "_id": chat_id
        }

        update = {
            "$set": {
                "history": []
            }
        }

        self.chat_collection.update_one(filter, update)