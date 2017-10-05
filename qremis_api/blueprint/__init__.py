import logging
from json import dumps, loads
from abc import ABCMeta, abstractmethod

from flask import Blueprint, jsonify
from flask_restful import Resource, Api, reqparse
import redis
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

import pyqremis


__version__ = "0.0.2"


BLUEPRINT = Blueprint('qremis_api', __name__)

BLUEPRINT.config = {}

API = Api(BLUEPRINT)


log = logging.getLogger(__name__)

record_kinds = ["object", "event", "agent", "rights", "relationship"]

pagination_args_parser = reqparse.RequestParser()
pagination_args_parser.add_argument('cursor', type=str, default="0")
pagination_args_parser.add_argument('limit', type=int, default=1000)


class Error(Exception):
    """Base class for exceptions in this module."""
    error_name = "Error"
    status_code = 500
    message = ""

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def to_dict(self):
        return {"message": self.message,
                "error_name": self.error_name}


class ConfigError(Error):
    pass


class UserError(Error):
    error_name = "UserError"
    status_code = 400


class ServerError(Error):
    error_name = "ServerError"
    status_code = 500


class NotFoundError(Error):
    error_name = "NotFoundError"
    status_code = 404


class DuplicateIdentifierError(UserError):
    error_name = "DuplicateIdentifierError"


class IdentifierDoesNotExistError(NotFoundError):
    error_name = "IdentifierDoesNotExistError"


class InvalidQremisRecordError(UserError):
    error_name = "InvalidQremisRecordError"


class MissingQremisUUIDIdentifierError(InvalidQremisRecordError):
    error_name = "MissingQremisUUIDIdentifierError"
    message = "The QREMIS record is missing a uuid identifier!"


@BLUEPRINT.errorhandler(Error)
def handle_errors(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


class StorageBackend(metaclass=ABCMeta):
    """ABC for storage backends, providing method requirements and footprints"""
    @abstractmethod
    def record_exists(self, kind, id):
        """
        Determines whether an identifier exists in the system

        __Args__

        1. kind (str): The kind of record (see module record_kinds)
        2. id (str): The identifier to determine the existence of

        __Returns__

        * (bool): whether or not the record exists
        """
        pass

    @abstractmethod
    def add_record(self, kind, id, rec):
        """
        Adds a record to the system

        __Args__

        1. kind (str): The kind of record (see module record_kinds)
        2. id (str): The identifier of the record to add
        3. rec (str): The JSON str representing the record
        """
        pass

    @abstractmethod
    def link_records(self, kind1, id1, kind2, id2):
        """
        Links two records together

        __Args__

        1. kind1 (str): The kind of the first record
        2. id1 (str): The identifier of the first record
        3. kind2 (str): The kind of the second record
        4. id2 (str): The identifier of the second record
        """
        # This method may impose limitations on the order of the "kinds"
        # that can be linked, and may also produce stub relationships
        # when required.
        pass

    @abstractmethod
    def get_record(self, id):
        """
        Retrieves a record

        __Args__

        1. id (str): The identifier of the record to retrieve


        __Returns__

        * (str): The record, as a JSON str
        """
        # Note: A lazy way for handling 404ing properly
        # is to call record_exists() in this function.
        # but if it's more effeciently to do some way
        # else in the storage implementation go with that.
        pass

    @abstractmethod
    def get_kind_links(self, kind, id, cursor, limit):
        """
        Returns a list of linked${kind} records related to the identified record

        __Args__

        1. kind (str): The kind of linked records to retrieve
        2. id (str): The identifier of the "originating" record to examine
        3. cursor (str): The starting cursor. "0" is always the default starting cursor
        4. limit (int/None): A suggestion for the number of results to return.
            if None is supplied the method attempts to return _all_ of the results.

        __Returns__

        * (str, [str]): The next cursor (or None) to use to produce more results,
            a list of identifiers
        """
        pass

    @abstractmethod
    def get_kind_list(self, kind, cursor, limit):
        """
        Returns a list of ${kind} record identifiers

        __Args__

        1. kind (str): The kind of record to list identifiers for
        2. cursor (str): The starting cursor. "0" is always the default starting cursor
        3. limit (int): A suggestion for the number of results to return.

        __Returns__

        * (str, [str]): The next cursor (or None) to use to produce more results,
            and a list of identifiers
        """
        pass


class RedisStorageBackend(StorageBackend):
    @staticmethod
    def validate_bp(bp):
        try:
            bp.config['REDIS_HOST']
        except KeyError:
            print(bp.config)
            raise ConfigError("No REDIS_HOST provided!")

    def __init__(self, bp):
        self.validate_bp(bp)
        self.redis = redis.StrictRedis(
            host=bp.config['REDIS_HOST'],
            port=bp.config.get("REDIS_PORT", 6379),
            db=bp.config.get("REDIS_DB")
        )

    def record_exists(self, kind, id):
        if kind not in record_kinds:
            raise AssertionError()
        log.debug("Checking for record existence: {} ({})".format(kind, id))
        return self.redis.zscore(kind+"List", id) is not None

    def add_record(self, kind, id, rec):
        if kind not in record_kinds:
            raise AssertionError()
        if self.record_exists(kind, id):
            raise DuplicateIdentifierError("Identifier {} already exists".format(str(id)))
        log.debug("Adding {} record with id {}".format(kind, id))
        self.redis.setnx(id, rec)
        self.redis.zadd(kind+"List", 0, id)

    def link_records(self, kind1, id1, kind2, id2):
        if kind1 not in record_kinds or kind2 not in record_kinds:
            raise AssertionError()
        if kind1 == "relationship" and kind2 != "relationship":
            raise AssertionError("It looks like you passed the arguments in the wrong order, " +
                                 "link_records() takes the relationship as the second set (" +
                                 "args[2] and args[3]) of arguments in order to not produce " +
                                 "an additional relationship entity")
        log.debug("Attempting to link {}({}) to {}({})".format(kind1, id1, kind2, id2))
#
# This code creates a stub relationship if you link any two other entities directly together
# with no intervening relationship. At the moment none of this code is exposed through the
# API itself, so I've commented it out.
#
#        kind3 = None
#        id3 = None
#        if kind2 != "relationship":
#            log.debug("target record is not a relationship - creating a simple " +
#                      "linking relationship")
#            kind3 = kind2
#            id3 = id2
#            kind2 = "relationship"
#            id2 = uuid4().hex
#            log.debug("Minting simple linking relationship ({})".format(id2))
#            relationship_record = pyqremis.Relationship(
#                pyqremis.RelationshipIdentifier(
#                    relationshipIdentifierType='uuid',
#                    relationshipIdentifierValue=uuid4().hex
#                ),
#                relationshipType="link",
#                relationshipSubType="simple",
#                relationshipNote="Automatically created to facilitate linking"
#            )
#            self.add_record(kind2, id2, dumps(relationship_record.to_dict()))
        self.redis.zadd(id1+"_"+kind2+"Links", 0, id2)
        self.redis.zadd(id2+"_"+kind1+"Links", 0, id1)
#        if kind3 is not None and id3 is not None:
#            self.redis.zadd(id2+"_"+kind3+"Links", 0, id3)
#            self.redis.zadd(id3+"_"+kind2+"Links", 0, id2)

    def get_record(self, id):
        try:
            return self.redis.get(id).decode("utf-8")
        except:
            raise IdentifierDoesNotExistError(str(id))

    def get_kind_links(self, kind, id, cursor, limit):
        # This is kind of like a non-generator version of zscan_iter, bounded
        # at the given limit (if a limit is set)
        # see: https://github.com/andymccurdy/redis-py/blob/master/redis/client.py
        # Note also the uncertainty in the "count" kwarg: https://redis.io/commands/scan#the-count-option
        # Thus the > 0.
        if kind not in record_kinds:
            raise AssertionError()
        results = []
        if limit:
            while cursor != 0 and limit > 0:
                cursor, data = self.redis.zscan(id+"_"+kind+"Links", cursor=cursor, count=limit)
                limit = limit - len(data)
                for item in data:
                    results.append(item)
        else:
            while cursor != 0:
                cursor, data = self.redis.zscan(id+"_"+kind+"Links", cursor=cursor, count=limit)
                for item in data:
                    results.append(item)
        return cursor, [x[0].decode("utf-8") for x in results]

    def get_kind_list(self, kind, cursor, limit):
        if kind not in record_kinds:
            raise AssertionError()
        results = []
        while cursor != 0 and limit > 0:
            cursor, data = self.redis.zscan(kind+"List", cursor=cursor, count=limit)
            limit = limit - len(data)
            for item in data:
                results.append(item)
        return cursor, [x[0].decode("utf-8") for x in results]


class MongoStorageBackend(StorageBackend):
    @staticmethod
    def validate_bp(bp):
        try:
            bp.config['MONGO_HOST']
        except KeyError:
            raise ConfigError("No MONGO_HOST provided!")
        try:
            bp.config['MONGO_DBNAME']
        except KeyError:
            raise ConfigError("No MONGO_DBNAME provided!")

    def __init__(self, bp):
        self.validate_bp(bp)
        self.client = MongoClient(bp.config['MONGO_HOST'], bp.config.get('MONGO_PORT', 27017))
        self.db = self.client[bp.config['MONGO_DBNAME']]

    def record_exists(self, kind, id):
        return bool(self.db['records'].find_one({'_id': id}))

    def add_record(self, kind, id, rec):
        try:
            self.db['records'].insert_one({'_id': id, 'rec': rec})
            self.db[kind+'List'].insert_one({'_id': id})
        except DuplicateKeyError:
            raise DuplicateIdentifierError("Identifier {} already exists".format(str(id)))

    def link_records(self, kind1, id1, kind2, id2):
        if kind1 not in record_kinds or kind2 not in record_kinds:
            raise AssertionError()
        if kind1 == "relationship" and kind2 != "relationship":
            raise AssertionError("It looks like you passed the argumnets in the wrong order, " +
                                 "link_records() takes the relationship as the second set (" +
                                 "args[2] and args[3]) of arguments in order to not produce " +
                                 "an additional relationship entity")
        log.debug("Attempting to link {}({}) to {}({})".format(kind1, id1, kind2, id2))
#        kind3 = None
#        id3 = None
#        if kind2 != "relationship":
#            log.debug("target record is not a relationship - creating a simple " +
#                      "linking relationship")
#            kind3 = kind2
#            id3 = id2
#            kind2 = "relationship"
#            id2 = uuid4().hex
#            log.debug("Minting simple linking relationship ({})".format(id2))
#            relationship_record = pyqremis.Relationship(
#                pyqremis.RelationshipIdentifier(
#                    relationshipIdentifierType='uuid',
#                    relationshipIdentifierValue=uuid4().hex
#                ),
#                relationshipType="link",
#                relationshipSubType="simple",
#                relationshipNote="Automatically created to facilitate linking"
#            )
#            self.add_record(kind2, id2, dumps(relationship_record.to_dict()))
        self.db[id1+'Linked'+kind2].insert_one({'_id': id2})
        self.db[id2+'Linked'+kind1].insert_one({'_id': id1})
#        if kind3 is not None and id3 is not None:
#            self.db[id2+'Linked'+kind3].insert_one({'_id': id3})
#            self.db[id3+'Linked'+kind2].insert_one({'_id': id2})

    def get_record(self, id):
        rec = self.db['records'].find_one({'_id': id})
        if rec is None:
            raise IdentifierDoesNotExistError(str(id))
        return rec['rec']

    def get_kind_links(self, kind, id, cursor, limit):
        def peek(cursor, limit):
            if len([x['_id'] for x in self.db[id+'Linked'+kind].find()\
                    .sort('_id', ASCENDING).skip(cursor+limit)]) > 0:
                return str(cursor+limit)
            return None
        cursor = int(cursor)
        if limit is not None:
            results = [x['_id'] for x in self.db[id+'Linked'+kind].find()\
                       .sort('_id', ASCENDING).skip(cursor).limit(limit)]
        else:
            results = [x['_id'] for x in self.db[id+'Linked'+kind].find()\
                       .sort('_id', ASCENDING).skip(cursor)]
        if limit:
            next_cursor = peek(cursor, limit)
        else:
            next_cursor = None
        return next_cursor, results

    def get_kind_list(self, kind, cursor, limit):
        def peek(cursor, limit):
            if len([x['_id'] for x in self.db[kind+'List'].find()\
                    .sort('_id', ASCENDING).skip(cursor+limit)]) > 0:
                return str(cursor+limit)
            return None
        cursor = int(cursor)
        results = [x['_id'] for x in self.db[kind+'List'].find()\
                   .sort('_id', ASCENDING).skip(cursor).limit(limit)]
        next_cursor = peek(cursor, limit)
        return next_cursor, results


def check_limit(limit):
    ub = BLUEPRINT.config.get("MAX_LIMIT", 1000)
    if limit > ub:
        log.warn(
            "Received request above MAX_LIMIT ({}), capping.".format(
                str(ub)
            )
        )
        limit = ub
    return limit


class Root(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        return {
            "object_list": API.url_for(ObjectList),
            "event_list": API.url_for(EventList),
            "agent_list": API.url_for(AgentList),
            "rights_list": API.url_for(RightsList),
            "relationship_list": API.url_for(RelationshipList)
        }


class ObjectList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_list("object", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['object_list'] = [{'id': x,
                             '_link': API.url_for(Object, id=x)}
                            for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        try:
            rec = pyqremis.Object.from_dict(loads(args['record']))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        objId = None
        for x in rec.get_objectIdentifier():
            if x.get_objectIdentifierType() == "uuid":
                objId = x.get_objectIdentifierValue()
        if objId is None:
            raise MissingQremisUUIDIdentifierError()
        relationships_to_link = []
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    relationships_to_link.append(x.get_linkingRelationshipIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        BLUEPRINT.config['storage'].add_record("object", objId, dumps(rec.to_dict()))
        for x in relationships_to_link:
            BLUEPRINT.config['storage'].link_records(
                "object", objId, "relationship", x
            )
        r = {}
        r['_link'] = API.url_for(Object, id=objId)
        r['id'] = objId
        return r


class Object(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Object.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        for x in BLUEPRINT.config['storage'].get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x
                )
            )
        return rec.to_dict()


class SparseObject(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Object.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        return rec.to_dict()


class ObjectLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x, '_link':  API.url_for(Relationship, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("object", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("relationship", args['relationship_id']):
            raise IdentifierDoesNotExistError(str(args['relationship_id']))
        BLUEPRINT.config['storage'].link_records("object", id, "relationship", args['relationship_id'])
        return id


class EventList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_list("event", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['event_list'] = [{'id': x, '_link': API.url_for(Event, id=x)}
                           for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        try:
            rec = pyqremis.Event.from_dict(loads(args['record']))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        eventId = None
        for x in rec.get_eventIdentifier():
            if x.get_eventIdentifierType() == "uuid":
                eventId = x.get_eventIdentifierValue()
        if eventId is None:
            raise MissingQremisUUIDIdentifierError()
        relationships_to_link = []
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    relationships_to_link.append(x.get_linkingRelationshipIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        BLUEPRINT.config['storage'].add_record("event", eventId, dumps(rec.to_dict()))
        for x in relationships_to_link:
            BLUEPRINT.config['storage'].link_records(
                "event", eventId, "relationship", x
            )
        r = {}
        r['_link'] = API.url_for(Event, id=eventId)
        r['id'] = eventId
        return r


class Event(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Event.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        for x in BLUEPRINT.config['storage'].get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x
                )
            )
        return rec.to_dict()


class SparseEvent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Event.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        return rec.to_dict()


class EventLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Relationship, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("event", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("relationship", args['relationship_id']):
            raise IdentifierDoesNotExistError(str(args['relationship_id']))
        BLUEPRINT.config['storage'].link_records("event", id, "relationship", args['relationship_id'])
        return id


class AgentList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_list("agent", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['agent_list'] = [{'id': x, '_link': API.url_for(Agent, id=x)}
                           for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        try:
            rec = pyqremis.Agent.from_dict(loads(args['record']))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        agentId = None
        for x in rec.get_agentIdentifier():
            if x.get_agentIdentifierType() == "uuid":
                agentId = x.get_agentIdentifierValue()
        if agentId is None:
            raise MissingQremisUUIDIdentifierError()
        relationships_to_link = []
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    relationships_to_link.append(x.get_linkingRelationshipIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        BLUEPRINT.config['storage'].add_record("agent", agentId, dumps(rec.to_dict()))
        for x in relationships_to_link:
            BLUEPRINT.config['storage'].link_records(
                "agent", agentId, "relationship", x
            )
        r = {}
        r['_link'] = API.url_for(Agent, id=agentId)
        r['id'] = agentId
        return r


class Agent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Agent.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        for x in BLUEPRINT.config['storage'].get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x
                )
            )
        return rec.to_dict()


class SparseAgent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Agent.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        return rec.to_dict()


class AgentLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Relationship, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("agent", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("relationship", args['relationship_id']):
            raise IdentifierDoesNotExistError(str(args['relationship_id']))
        BLUEPRINT.config['storage'].link_records("agent", id, "relationship", args['relationship_id'])
        return id


class RightsList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_list("rights", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['rights_list'] = [{'id': x, '_link': API.url_for(Rights, id=x)}
                            for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        try:
            rec = pyqremis.Rights.from_dict(loads(args['record']))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        rightsId = None
        for x in rec.get_rightsIdentifier():
            if x.get_rightsIdentifierType() == "uuid":
                rightsId = x.get_rightsIdentifierValue()
        if rightsId is None:
            raise MissingQremisUUIDIdentifierError()
        relationships_to_link = []
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    relationships_to_link.append(x.get_linkingRelationshipIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        BLUEPRINT.config['storage'].add_record("rights", rightsId, dumps(rec.to_dict()))
        for x in relationships_to_link:
            BLUEPRINT.config['storage'].link_records(
                "rights", rightsId, "relationship", x
            )
        r = {}
        r['_link'] = API.url_for(Rights, id=rightsId)
        r['id'] = rightsId
        return r


class Rights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Rights.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        for x in BLUEPRINT.config['storage'].get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x
                )
            )
        return rec.to_dict()


class SparseRights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Rights.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        return rec.to_dict()


class RightsLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Relationship, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("rights", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("relationship", args['relationship_id']):
            raise IdentifierDoesNotExistError(str(args['relationship_id']))
        BLUEPRINT.config['storage'].link_records("rights", id, "relationship", args['relationship_id'])
        return id


class RelationshipList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_list("relationship", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['relationship_list'] = [
            {'id': x, '_link': API.url_for(Relationship, id=x)}
            for x in q[1]
        ]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        try:
            rec = pyqremis.Relationship.from_dict(loads(args['record']))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        relationshipId = None
        for x in rec.get_relationshipIdentifier():
            if x.get_relationshipIdentifierType() == "uuid":
                relationshipId = x.get_relationshipIdentifierValue()
        if relationshipId is None:
            raise MissingQremisUUIDIdentifierError()

        objects_to_link = []
        try:
            for x in rec.get_linkingObjectIdentifier():
                if x.get_linkingObjectIdentifierType() == "uuid":
                    objects_to_link.append(x.get_linkingObjectIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingObjectIdentifier()
        except KeyError:
            pass

        events_to_link = []
        try:
            for x in rec.get_linkingEventIdentifier():
                if x.get_linkingEventIdentifierType() == "uuid":
                    events_to_link.append(x.get_linkingEventIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingEventIdentifier()
        except KeyError:
            pass

        agents_to_link = []
        try:
            for x in rec.get_linkingAgentIdentifier():
                if x.get_linkingAgentIdentifierType() == "uuid":
                    agents_to_link.append(x.get_linkingAgentIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingAgentIdentifier()
        except KeyError:
            pass

        rights_to_link = []
        try:
            for x in rec.get_linkingRightsIdentifier():
                if x.get_linkingRightsIdentifierType() == "uuid":
                    rights_to_link.append(x.get_linkingRightsIdentifierValue())
                else:
                    raise MissingQremisUUIDIdentifierError()
            rec.del_linkingRightsIdentifier()
        except KeyError:
            pass

        BLUEPRINT.config['storage'].add_record("relationship", relationshipId, dumps(rec.to_dict()))
        for x in objects_to_link:
            BLUEPRINT.config['storage'].link_records(
                "object", x, "relationship", relationshipId
            )
        for x in events_to_link:
            BLUEPRINT.config['storage'].link_records(
                "event", x, "relationship", relationshipId
            )
        for x in agents_to_link:
            BLUEPRINT.config['storage'].link_records(
                "agent", x, "relationship", relationshipId
            )
        for x in rights_to_link:
            BLUEPRINT.config['storage'].link_records(
                "rights", x, "relationship", relationshipId
            )

        r = {}
        r['_link'] = API.url_for(Relationship, id=relationshipId)
        r['id'] = relationshipId
        return r


class Relationship(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Relationship.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))

        for x in BLUEPRINT.config['storage'].get_kind_links("object", id, "0", None)[1]:
            rec.add_linkingObjectIdentifier(
                pyqremis.LinkingObjectIdentifier(
                    linkingObjectIdentifierType="uuid",
                    linkingObjectIdentifierValue=x
                )
            )

        for x in BLUEPRINT.config['storage'].get_kind_links("agent", id, "0", None)[1]:
            rec.add_linkingAgentIdentifier(
                pyqremis.LinkingAgentIdentifier(
                    linkingAgentIdentifierType="uuid",
                    linkingAgentIdentifierValue=x
                )
            )

        for x in BLUEPRINT.config['storage'].get_kind_links("event", id, "0", None)[1]:
            rec.add_linkingEventIdentifier(
                pyqremis.LinkingEventIdentifier(
                    linkingEventIdentifierType="uuid",
                    linkingEventIdentifierValue=x
                )
            )

        for x in BLUEPRINT.config['storage'].get_kind_links("rights", id, "0", None)[1]:
            rec.add_linkingRightsIdentifier(
                pyqremis.LinkingRightsIdentifier(
                    linkingRightsIdentifierType="uuid",
                    linkingRightsIdentifierValue=x
                )
            )
        return rec.to_dict()


class SparseRelationship(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        rec_str = BLUEPRINT.config['storage'].get_record(id)
        try:
            rec = pyqremis.Relationship.from_dict(loads(rec_str))
        except Exception as e:
            raise InvalidQremisRecordError(str(e))
        return rec.to_dict()


class RelationshipLinkedObjects(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("object", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingObjectIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Object, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("object_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("relationship", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("object", args['object_id']):
            raise IdentifierDoesNotExistError(str(args['object_id']))
        BLUEPRINT.config['storage'].link_records("object", args['object_id'], "relationship", id)
        return id


class RelationshipLinkedEvents(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("event", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingEventIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Event, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("event_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("relationship", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("event", args['event_id']):
            raise IdentifierDoesNotExistError(str(args['event_id']))
        BLUEPRINT.config['storage'].link_records("event", args['event_id'], "relationship", id)
        return id


class RelationshipLinkedAgents(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("agent", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingAgentIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Agent, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("agent_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("relationship", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("agent", args['agent_id']):
            raise IdentifierDoesNotExistError(str(args['agent_id']))
        BLUEPRINT.config['storage'].link_records("agent", args['agent_id'], "relationship", id)
        return id


class RelationshipLinkedRights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = BLUEPRINT.config['storage'].get_kind_links("rights", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRightsIdentifier_list'] = [
            {'id': x, '_link': API.url_for(Rights, id=x)}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("rights_id", type=str, required=True)
        args = parser.parse_args()
        if not BLUEPRINT.config['storage'].record_exists("relationship", id):
            raise IdentifierDoesNotExistError(str(id))
        if not BLUEPRINT.config['storage'].record_exists("rights", args['rights_id']):
            raise IdentifierDoesNotExistError(str(args['rights_id']))
        BLUEPRINT.config['storage'].link_records("rights", args['rights_id'], "relationship", id)
        return id


class Version(Resource):
    def get(self):
        return {"version": __version__}

@BLUEPRINT.record
def handle_configs(setup_state):
    app = setup_state.app
    BLUEPRINT.config.update(app.config)
    if BLUEPRINT.config.get('DEFER_CONFIG'):
        return

    storage_backends = {
        'redis': RedisStorageBackend,
        'mongo': MongoStorageBackend
    }

    # Configure the selected storage backend
    if not BLUEPRINT.config.get('STORAGE_BACKEND'):
        raise ConfigError("No STORAGE_BACKEND value provided!")
    elif BLUEPRINT.config['STORAGE_BACKEND'] not in storage_backends:
        raise ConfigError(
            "Invalid storage backend! Valid options: {}".format(
                ", ".join([x for x in storage_backends.keys()])
            )
        )
    else:
        BLUEPRINT.config['storage'] = storage_backends[BLUEPRINT.config['STORAGE_BACKEND']](BLUEPRINT)

    if BLUEPRINT.config.get("VERBOSITY"):
        logging.basicConfig(level=BLUEPRINT.config['VERBOSITY'])
    else:
        logging.basicConfig(level="WARN")


API.add_resource(Root, "/")

API.add_resource(ObjectList, "/object_list")
API.add_resource(Object, "/object_list/<string:id>")
API.add_resource(SparseObject, "/object_list/<string:id>/sparse")
API.add_resource(ObjectLinkedRelationships, "/object_list/<string:id>/linkedRelationships")

API.add_resource(EventList, "/event_list")
API.add_resource(Event, "/event_list/<string:id>")
API.add_resource(SparseEvent, "/event_list/<string:id>/sparse")
API.add_resource(EventLinkedRelationships, "/event_list/<string:id>/linkedRelationships")

API.add_resource(AgentList, "/agent_list")
API.add_resource(Agent, "/agent_list/<string:id>")
API.add_resource(SparseAgent, "/agent_list/<string:id>/sparse")
API.add_resource(AgentLinkedRelationships, "/agent_list/<string:id>/linkedRelationships")

API.add_resource(RightsList, "/rights_list")
API.add_resource(Rights, "/rights_list/<string:id>")
API.add_resource(SparseRights, "/rights_list/<string:id>/sparse")
API.add_resource(RightsLinkedRelationships, "/rights_list/<string:id>/linkedRelationships")

API.add_resource(RelationshipList, "/relationship_list")
API.add_resource(Relationship, "/relationship_list/<string:id>")
API.add_resource(SparseRelationship, "/relationship_list/<string:id>/sparse")
API.add_resource(RelationshipLinkedObjects, "/relationship_list/<string:id>/linkedObjects")
API.add_resource(RelationshipLinkedEvents, "/relationship_list/<string:id>/linkedEvents")
API.add_resource(RelationshipLinkedAgents, "/relationship_list/<string:id>/linkedAgents")
API.add_resource(RelationshipLinkedRights, "/relationship_list/<string:id>/linkedRights")

API.add_resource(Version, '/version')
