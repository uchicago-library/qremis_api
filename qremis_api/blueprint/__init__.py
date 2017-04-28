import logging
from uuid import uuid4
from json import dumps, loads

from flask import Blueprint, abort
from flask_restful import Resource, Api, reqparse
import redis

import pyqremis


BLUEPRINT = Blueprint('qremis_api', __name__)


BLUEPRINT.config = {
    'redis': None,
    'REDIS_HOST': None,
    'REDIS_DB': None
}


API = Api(BLUEPRINT)


log = logging.getLogger(__name__)


pagination_args_parser = reqparse.RequestParser()
pagination_args_parser.add_argument('cursor', type=str, default="0")
pagination_args_parser.add_argument('limit', type=int, default=1000)


record_kinds = ["object", "event", "agent", "rights", "relationship"]


def check_limit(limit):
    if limit > BLUEPRINT.config.get("MAX_LIMIT", 1000):
        log.warn(
            "Received request above MAX_LIMIT ({}), capping.".format(str(BLUEPRINT.config.get("MAX_LIMIT", 1000)))
        )
        limit = BLUEPRINT.config.get("MAX_LIMIT", 1000)
    return limit


def record_exists(kind, id):
    if kind not in record_kinds:
        raise AssertionError()
    log.debug("Checking for record existence: {} ({})".format(kind, id))
    return BLUEPRINT.config['redis'].zscore(kind+"List", id) is not None


def add_record(kind, id, rec):
    if kind not in record_kinds:
        raise AssertionError()
    log.debug("Adding {} record with id {}".format(kind, id))
    BLUEPRINT.config['redis'].setnx(id, rec)
    BLUEPRINT.config['redis'].zadd(kind+"List", 0, id)


def link_records(kind1, id1, kind2, id2):
    if kind1 not in record_kinds or kind2 not in record_kinds:
        raise AssertionError()
    if kind1 == "relationship" and kind2 != "relationship":
        raise ValueError("It looks like you passed the argumnets in the wrong order, " +
                         "link_records() takes the relationship as the second set (" +
                         "args[2] and args[3]) of arguments in order to not produce " +
                         "an additional relationship entity")
    log.debug("Attempting to link {}({}) to {}({})".format(kind1, id1, kind2, id2))
    kind3 = None
    id3 = None
    if kind2 != "relationship":
        log.debug("target record is not a relationship - creating a simple " +
                  "linking relationship")
        kind3 = kind2
        id3 = id2
        kind2 = "relationship"
        id2 = uuid4().hex
        log.debug("Minting simple linking relationship ({})".format(id2))
        relationship_record = pyqremis.Relationship(
            pyqremis.RelationshipIdentifier(
                relationshipIdentifierType='uuid',
                relationshipIdentifierValue=uuid4().hex
            ),
            relationshipType="link",
            relationshipSubType="simple",
            relationshipNote="Automatically created to facilitate linking"
        )
        add_record(kind2, id2, dumps(relationship_record.to_dict()))
    # This puts kind of a lot of responsibility on the client to dissect the records
    # before POSTing them and working with linking aftwards
    # Eg, you can't just say "this is linked to a thing I'm going to add later"
    # Instead you have to look back through your objects (that you've taken apart)
    # in your app space saying "and now I will re-establish that object X participates in
    # relationship Y"
    # if not record_exists(kind1, id1) or not record_exists(kind2, id2):
    #     raise ValueError("A targeted record does not exist")
    # if kind3 is not None and not record_exists(kind3, id3):
    #     raise ValueError("A targeted record does not exist")
    # Bidirectional linking
    BLUEPRINT.config['redis'].zadd(id1+"_"+kind2+"Links", 0, id2)
    BLUEPRINT.config['redis'].zadd(id2+"_"+kind1+"Links", 0, id1)
    if kind3 is not None and id3 is not None:
        BLUEPRINT.config['redis'].zadd(id2+"_"+kind3+"Links", 0, id3)
        BLUEPRINT.config['redis'].zadd(id3+"_"+kind2+"Links", 0, id2)


def get_record(id):
    try:
        return BLUEPRINT.config['redis'].get(id).decode("utf-8")
    except:
        raise ValueError("Element {} doesn't exist!".format(id))


def record_is_kind(kind, id):
    if kind not in record_kinds:
        raise AssertionError()
    log.debug("Determining if record {} is {}".format(id, kind))
    for x in BLUEPRINT.config['redis'].zscan_iter(kind+"List"):
        if x[0].decode("utf-8") == id:
            log.debug("Record {} is a(n) {}".format(id, kind))
            return True
    log.debug("Record {} is not a(n) {}".format(id, kind))
    return False


def get_kind_links(kind, id, cursor, limit):
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
            cursor, data = BLUEPRINT.config['redis'].zscan(id+"_"+kind+"Links", cursor=cursor, count=limit)
            limit = limit - len(data)
            for item in data:
                results.append(item)
    else:
        while cursor != 0:
            cursor, data = BLUEPRINT.config['redis'].zscan(id+"_"+kind+"Links", cursor=cursor, count=limit)
            for item in data:
                results.append(item)
    return cursor, results


def get_kind_list(kind, cursor, limit):
    if kind not in record_kinds:
        raise AssertionError()
    return BLUEPRINT.config['redis'].zscan(kind+"List", cursor, count=limit)


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
        q = get_kind_list("object", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['object_list'] = [{'id': x[0].decode('utf-8'),
                             '_link': API.url_for(Object, id=x[0].decode('utf-8'))}
                            for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        rec = pyqremis.Object.from_dict(loads(args['record']))
        objId = None
        for x in rec.get_objectIdentifier():
            if x.get_objectIdentifierType() == "uuid":
                objId = x.get_objectIdentifierValue()
        if objId is None:
            raise RuntimeError()
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    link_records("object", objId, "relationship", x.get_linkingRelationshipIdentifierValue())
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        add_record("object", objId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Object, id=objId)
        r['id'] = objId
        return r


class Object(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("object", id):
            abort(404)
        rec = pyqremis.Object.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class SparseObject(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("object", id):
            abort(404)
        rec = pyqremis.Object.from_dict(loads(get_record(id)))
        return rec.to_dict()


class ObjectLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link':  API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("object", id):
            raise ValueError("No such object identifier! ({})".format(id))
        if not record_exists("relationship", args['relationship_id']):
            raise ValueError("No such relationship identifier! ({})".format(args['relationship_id']))
        link_records("object", id, "relationship", args['relationship_id'])
        return id


class EventList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("event", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['event_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Event, id=x[0].decode('utf-8'))}
                           for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        rec = pyqremis.Event.from_dict(loads(args['record']))
        eventId = None
        for x in rec.get_eventIdentifier():
            if x.get_eventIdentifierType() == "uuid":
                eventId = x.get_eventIdentifierValue()
        if eventId is None:
            raise RuntimeError()
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    link_records("event", eventId, "relationship", x.get_linkingRelationshipIdentifierValue())
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        add_record("event", eventId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Event, id=eventId)
        r['id'] = eventId
        return r


class Event(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("event", id):
            abort(404)
        rec = pyqremis.Event.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class SparseEvent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("event", id):
            abort(404)
        rec = pyqremis.Event.from_dict(loads(get_record(id)))
        return rec.to_dict()


class EventLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("event", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existent identifier!")
        link_records("event", id, "relationship", args['relationship_id'])
        return id


class AgentList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("agent", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['agent_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Agent, id=x[0].decode('utf-8'))}
                           for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        rec = pyqremis.Agent.from_dict(loads(args['record']))
        agentId = None
        for x in rec.get_agentIdentifier():
            if x.get_agentIdentifierType() == "uuid":
                agentId = x.get_agentIdentifierValue()
        if agentId is None:
            raise RuntimeError()
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    link_records("agent", agentId, "relationship", x.get_linkingRelationshipIdentifierValue())
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        add_record("agent", agentId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Agent, id=agentId)
        r['id'] = agentId
        return r


class Agent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("agent", id):
            abort(404)
        rec = pyqremis.Agent.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class SparseAgent(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("agent", id):
            abort(404)
        rec = pyqremis.Agent.from_dict(loads(get_record(id)))
        return rec.to_dict()


class AgentLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("agent", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existent identifier!")
        link_records("agent", id, "relationship", args['relationship_id'])
        return id


class RightsList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("rights", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['rights_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Rights, id=x[0].decode('utf-8'))}
                            for x in q[1]]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        rec = pyqremis.Rights.from_dict(loads(args['record']))
        rightsId = None
        for x in rec.get_rightsIdentifier():
            if x.get_rightsIdentifierType() == "uuid":
                rightsId = x.get_rightsIdentifierValue()
        if rightsId is None:
            raise RuntimeError()
        try:
            for x in rec.get_linkingRelationshipIdentifier():
                if x.get_linkingRelationshipIdentifierType() == "uuid":
                    link_records("rights", rightsId, "relationship", x.get_linkingRelationshipIdentifierValue())
            rec.del_linkingRelationshipIdentifier()
        except KeyError:
            pass
        add_record("rights", rightsId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Rights, id=rightsId)
        r['id'] = rightsId
        return r


class Rights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("rights", id):
            abort(404)
        rec = pyqremis.Rights.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, "0", None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class SparseRights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("rights", id):
            abort(404)
        rec = pyqremis.Rights.from_dict(loads(get_record(id)))
        return rec.to_dict()


class RightsLinkedRelationships(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("rights", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existent identifier!")
        link_records("rights", id, "relationship", args['relationship_id'])
        return id


class RelationshipList(Resource):
    def get(self):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("relationship", args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['relationship_list'] = [
            {'id': x[0].decode('utf-8'), '_link': API.url_for(Relationship, id=x[0].decode('utf-8'))}
            for x in q[1]
        ]
        return r

    def post(self):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("record", type=str, required=True)
        args = parser.parse_args()
        rec = pyqremis.Relationship.from_dict(loads(args['record']))
        relationshipId = None
        for x in rec.get_relationshipIdentifier():
            if x.get_relationshipIdentifierType() == "uuid":
                relationshipId = x.get_relationshipIdentifierValue()
        if relationshipId is None:
            raise RuntimeError()

        try:
            for x in rec.get_linkingObjectIdentifier():
                if x.get_linkingObjectIdentifierType() == "uuid":
                    link_records("object", x.get_linkingObjectIdentifierValue(), "relationship", relationshipId)
            rec.del_linkingObjectIdentifier()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingEventIdentifier():
                if x.get_linkingEventIdentifierType() == "uuid":
                    link_records("event", x.get_linkingEventIdentifierValue(), "relationship", relationshipId)
            rec.del_linkingEventIdentifier()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingAgentIdentifier():
                if x.get_linkingAgentIdentifierType() == "uuid":
                    link_records("agent", x.get_linkingAgentIdentifierValue(), "relationship", relationshipId)
            rec.del_linkingAgentIdentifier()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingRightsIdentifier():
                if x.get_linkingRightsIdentifierType() == "uuid":
                    link_records("rights", x.get_linkingRightsIdentifierValue(), "relationship", relationshipId)
            rec.del_linkingRightsIdentifier()
        except KeyError:
            pass

        add_record("relationship", relationshipId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Relationship, id=relationshipId)
        r['id'] = relationshipId
        return r


class Relationship(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("relationship", id):
            abort(404)
        rec = pyqremis.Relationship.from_dict(loads(get_record(id)))

        for x in get_kind_links("object", id, "0", None)[1]:
            rec.add_linkingObjectIdentifier(
                pyqremis.LinkingObjectIdentifier(
                    linkingObjectIdentifierType="uuid",
                    linkingObjectIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("agent", id, "0", None)[1]:
            rec.add_linkingAgentIdentifier(
                pyqremis.LinkingAgentIdentifier(
                    linkingAgentIdentifierType="uuid",
                    linkingAgentIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("event", id, "0", None)[1]:
            rec.add_linkingEventIdentifier(
                pyqremis.LinkingEventIdentifier(
                    linkingEventIdentifierType="uuid",
                    linkingEventIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("rights", id, "0", None)[1]:
            rec.add_linkingRightsIdentifier(
                pyqremis.LinkingRightsIdentifier(
                    linkingRightsIdentifierType="uuid",
                    linkingRightsIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class SparseRelationship(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        if not record_exists("relationship", id):
            abort(404)
        rec = pyqremis.Relationship.from_dict(loads(get_record(id)))
        return rec.to_dict()


class RelationshipLinkedObjects(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("object", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingObjectIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Object, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("object_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("object", args['object_id']):
            raise ValueError("Non-existent identifier!")
        link_records("object", args['object_id'], "relationship", id)
        return id


class RelationshipLinkedEvents(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("event", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingEventIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Event, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("event_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("event", args['event_id']):
            raise ValueError("Non-existent identifier!")
        link_records("event", args['event_id'], "relationship", id)
        return id


class RelationshipLinkedAgents(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("agent", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingAgentIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Agent, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("agent_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("agent", args['agent_id']):
            raise ValueError("Non-existent identifier!")
        link_records("agent", args['agent_id'], "relationship", id)
        return id


class RelationshipLinkedRights(Resource):
    def get(self, id):
        log.debug("GET received @ {}".format(self.__class__.__name__))
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("rights", id, args['cursor'], check_limit(args['limit']))
        r['pagination'] = {}
        r['pagination']['starting_cursor'] = args['cursor']
        r['pagination']['next_cursor'] = q[0] if q[0] != 0 else None
        r['pagination']['limit'] = check_limit(args['limit'])
        r['linkingRightsIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Rights, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        log.debug("POST received @ {}".format(self.__class__.__name__))
        parser = reqparse.RequestParser()
        parser.add_argument("rights_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id):
            raise ValueError("Non-existent identifier!")
        if not record_exists("rights", args['rights_id']):
            raise ValueError("Non-existent identifier!")
        link_records("rights", args['rights_id'], "relationship", id)
        return id


@BLUEPRINT.record
def handle_configs(setup_state):
    app = setup_state.app
    BLUEPRINT.config.update(app.config)

    BLUEPRINT.config['redis'] = redis.StrictRedis(
        host=BLUEPRINT.config['REDIS_HOST'],
        port=BLUEPRINT.config.get("REDIS_PORT", 6379),
        db=BLUEPRINT.config.get("REDIS_DB")
    )

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
