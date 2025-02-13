﻿using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace FeatureFlagsCo.Messaging.Models
{
    public abstract class MongoModelBase 
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public string Id { get; set; }

        public abstract string GetCollectionName();
    }
}
