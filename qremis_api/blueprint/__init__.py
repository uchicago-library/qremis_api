import logging
from uuid import uuid4
from json import dumps, loads

from flask import Blueprint
from flask_restful import Resource, Api, reqparse
import redis

import pyqremis


BLUEPRINT = Blueprint('qremis_api', __name__)


BLUEPRINT.config = {}


API = Api(BLUEPRINT)


log = logging.getLogger(__name__)


pagination_args_parser = reqparse.RequestParser()
pagination_args_parser.add_argument('cursor', type=int, default=0)
pagination_args_parser.add_argument('limit', type=int, default=1000)


def check_limit(limit):
    if limit > BLUEPRINT.config.get("MAX_LIMIT", 1000):
        log.warn(
            "Received request above MAX_LIMIT (or 1000 if undefined), capping.")
        limit = BLUEPRINT.config.get("MAX_LIMIT", 1000)
    return limit


def record_exists(kind, id):
    return BLUEPRINT.config['redis'].zscore(kind+"List", id) is not None


def add_record(kind, id, rec):
    BLUEPRINT.config['redis'].setnx(id, rec)
    BLUEPRINT.config['redis'].zadd(kind+"List", 0, id)


def link_records(kind1, id1, kind2, id2):
    kind3 = None
    id3 = None
    # This puts kind of a lot of responsibility on the client to dissect the records
    # before POSTing them and working with linking aftwards
    # Eg, you can't just say "this is linked to a thing I'm going to add later"
    # Instead you have to look back through your objects (that you've taken apart)
    # in your app space saying "and now I will re-establish that object X participates in
    # relationship Y"
#    if not record_exists(kind1, id1) or not record_exists(kind2, id2):
#        raise ValueError("A targeted record does not exist")
    if kind2 != "relationship":
        kind3 = kind2
        id3 = id2
        kind2 = "relationship"
        id2 = uuid4().hex
        relationship_record = pyqremis.Relationship(
            pyqremis.RelationshipIdentifier(
                relationshipIdentifierType='uuid',
                relationshipIdentifierValue=uuid4().hex
            ),
            relationshipType="link",
            relationshipSubType="simple",
            relationshipNote="Automatically created to facilitate linking"
        )
        add_record(kind2, id2, dumps(relationship_record.to_json()))
    BLUEPRINT.config['redis'].zadd(id1+"_"+kind2+"Links", 0, id2)
    BLUEPRINT.config['redis'].zadd(id2+"_"+kind1+"Links", 0, id1)
    if kind3 is not None and id3 is not None:
        BLUEPRINT.config['redis'].zadd(id3+"_"+kind3+"Links", 0, id3)


def get_record(id):
    try:
        return BLUEPRINT.config['redis'].get(id).decode("utf-8")
    except:
        raise ValueError("Element {} doesn't exist!".format(id))


def record_is_kind(kind, id):
    for x in BLUEPRINT.config['redis'].zscan_iter(kind+"List"):
        if x[0].decode("utf-8") == id:
            return True
    return False


def get_kind_links(kind, id, cursor, limit):
    return BLUEPRINT.config['redis'].zscan(id+"_"+kind+"Links", cursor=cursor, count=limit)


def get_kind_list(kind, cursor, limit):
    return BLUEPRINT.config['redis'].zscan(kind+"List", cursor, count=limit)


class Root(Resource):
    def get(self):
        return {
            "object_list": API.url_for(ObjectList),
            "event_list": API.url_for(EventList),
            "agent_list": API.url_for(AgentList),
            "rights_list": API.url_for(RightsList),
            "relationship_list": API.url_for(RelationshipList)
        }


class ObjectList(Resource):
    def get(self):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("object", args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['object_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Object, id=x[0].decode('utf-8'))}
                            for x in q[1]]
        return r

    def post(self):
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
        if not record_exists("object", id):
            raise ValueError("No such object! ({})".format(id))
        rec = pyqremis.Object.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, 0, None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class ObjectLinkedRelationships(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link':  API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("object", id):
            raise ValueError("No such object identifier! ({})".format(id))
        if not record_exists("relationship", args['relationship_id']):
            raise ValueError("No such relationship identifier! ({})".format(args['relationship_id']))
        link_records("object", id, "relationship", args['relationship_id'])


class EventList(Resource):
    def get(self):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("event", args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['event_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Event, id=x[0].decode('utf-8'))}
                           for x in q[1]]
        return r

    def post(self):
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
        if not record_exists("event", id):
            raise ValueError("No such event! ({})".format(id))
        rec = pyqremis.Event.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, 0, None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class EventLinkedRelationships(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("event", id) or not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existant identifier!")
        link_records("event", id, "relationship", args['relationship_id'])


class AgentList(Resource):
    def get(self):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("agent", args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['agent_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Agent, id=x[0].decode('utf-8'))}
                           for x in q[1]]
        return r

    def post(self):
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
        if not record_exists("agent", id):
            raise ValueError("No such agent! ({})".format(id))
        rec = pyqremis.Agent.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, 0, None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()

    def post(self):
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
        for x in rec.get_linkingRelationshipIdentifier():
            if x.get_linkingRelationshipIdentifierType() == "uuid":
                link_records("agent", agentId, "relationship", x.get_linkingRelationshipIdentifierValue())
        rec.del_linkingRelationshipIdentifier()
        add_record("agent", agentId, dumps(rec.to_dict()))
        return API.url_for(Agent, id=agentId)


class AgentLinkedRelationships(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("agent", id) or not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existant identifier!")
        link_records("agent", id, "relationship", args['relationship_id'])


class RightsList(Resource):
    def get(self):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("rights", args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['rights_list'] = [{'id': x[0].decode('utf-8'), '_link': API.url_for(Rights, id=x[0].decode('utf-8'))}
                            for x in q[1]]
        return r

    def post(self):
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
        if not record_exists("rights", id):
            raise ValueError("No such rights! ({})".format(id))
        rec = pyqremis.Rights.from_dict(loads(get_record(id)))
        for x in get_kind_links("relationship", id, 0, None)[1]:
            rec.add_linkingRelationshipIdentifier(
                pyqremis.LinkingRelationshipIdentifier(
                    linkingRelationshipIdentifierType="uuid",
                    linkingRelationshipIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class RightsLinkedRelationships(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("relationship", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingRelationshipIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Relationship, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("relationship_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("rights", id) or not record_exists("relationship", args['relationship_id']):
            raise ValueError("Non-existant identifier!")
        link_records("rights", id, "relationship", args['relationship_id'])


class RelationshipList(Resource):
    def get(self):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_list("relationship", args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['relationship_list'] = [
            {'id': x[0].decode('utf-8'), '_link': API.url_for(Relationship, id=x[0].decode('utf-8'))}
            for x in q[1]
        ]
        return r

    def post(self):
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
                    link_records("relationship", relationshipId, "object", x.get_linkingObjectIdentifierValue())
            rec.del_linkingObjectIdenitifer()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingEventIdentifier():
                if x.get_linkingEventIdentifierType() == "uuid":
                    link_records("relationship", relationshipId, "event", x.get_linkingEventIdentifierValue())
            rec.del_linkingEventIdenitifer()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingAgentIdentifier():
                if x.get_linkingAgentIdentifierType() == "uuid":
                    link_records("relationship", relationshipId, "agent", x.get_linkingAgentIdentifierValue())
            rec.del_linkingAgentIdenitifer()
        except KeyError:
            pass

        try:
            for x in rec.get_linkingRightsIdentifier():
                if x.get_linkingRightsIdentifierType() == "uuid":
                    link_records("relationship", relationshipId, "rights", x.get_linkingRightsIdentifierValue())
            rec.del_linkingRightsIdenitifer()
        except KeyError:
            pass

        add_record("relationship", relationshipId, dumps(rec.to_dict()))
        r = {}
        r['_link'] = API.url_for(Relationship, id=relationshipId)
        r['id'] = relationshipId
        return r


class Relationship(Resource):
    def get(self, id):
        if not record_exists("relationship", id):
            raise ValueError("No such relationship! ({})".format(id))
        rec = pyqremis.Relationship.from_dict(loads(get_record(id)))

        for x in get_kind_links("object", id, 0, None)[1]:
            rec.add_linkingObjectIdentifier(
                pyqremis.LinkingObjectIdentifier(
                    linkingObjectIdentifierType="uuid",
                    linkingObjectIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("agent", id, 0, None)[1]:
            rec.add_linkingAgentIdentifier(
                pyqremis.LinkingAgentIdentifier(
                    linkingAgentIdentifierType="uuid",
                    linkingAgentIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("event", id, 0, None)[1]:
            rec.add_linkingEventIdentifier(
                pyqremis.LinkingEventIdentifier(
                    linkingEventIdentifierType="uuid",
                    linkingEventIdentifierValue=x[0].decode("utf-8")
                )
            )

        for x in get_kind_links("rights", id, 0, None)[1]:
            rec.add_linkingRightsIdentifier(
                pyqremis.LinkingRightsIdentifier(
                    linkingRightsIdentifierType="uuid",
                    linkingRightsIdentifierValue=x[0].decode("utf-8")
                )
            )
        return rec.to_dict()


class RelationshipLinkedObjects(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("object", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingObjectIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Object, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("object_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id) or not record_exists("object", args['object_id']):
            raise ValueError("Non-existant identifier!")
        link_records("relationship", id, "object", args['object_id'])


class RelationshipLinkedEvents(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("event", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingEventIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Event, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("event_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id) or not record_exists("event", args['event_id']):
            raise ValueError("Non-existant identifier!")
        link_records("relationship", id, "event", args['event_id'])


class RelationshipLinkedAgents(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("agent", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingAgentIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Agent, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("agent_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id) or not record_exists("agent", args['agent_id']):
            raise ValueError("Non-existant identifier!")
        link_records("relationship", id, "agent", args['agent_id'])


class RelationshipLinkedRights(Resource):
    def get(self, id):
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        r = {}
        q = get_kind_links("rights", id, args['cursor'], check_limit(args['limit']))
        r['starting_cursor'] = args['cursor']
        r['next_cursor'] = q[0] if q[0] != 0 else None
        r['limit'] = check_limit(args['limit'])
        r['linkingRightsIdentifier_list'] = [
            {'id': x[0].decode("utf-8"), '_link': API.url_for(Rights, id=x[0].decode("utf-8"))}
            for x in q[1]
        ]
        return r

    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("rights_id", type=str, required=True)
        args = parser.parse_args()
        if not record_exists("relationship", id) or not record_exists("rights", args['rights_id']):
            raise ValueError("Non-existant identifier!")
        link_records("relationship", id, "rights", args['rights_id'])


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
API.add_resource(ObjectLinkedRelationships, "/object_list/<string:id>/linkedRelationships")

API.add_resource(EventList, "/event_list")
API.add_resource(Event, "/event_list/<string:id>")
API.add_resource(EventLinkedRelationships, "/event_list/<string:id>/linkedRelationships")

API.add_resource(AgentList, "/agent_list")
API.add_resource(Agent, "/agent_list/<string:id>")
API.add_resource(AgentLinkedRelationships, "/agent_list/<string:id>/linkedRelationships")

API.add_resource(RightsList, "/rights_list")
API.add_resource(Rights, "/rights_list/<string:id>")
API.add_resource(RightsLinkedRelationships, "/rights_list/<string:id>/linkedRelationships")

API.add_resource(RelationshipList, "/relationship_list")
API.add_resource(Relationship, "/relationship_list/<string:id>")
API.add_resource(RelationshipLinkedObjects, "/relationship_list/<string:id>/linkedObjects")
API.add_resource(RelationshipLinkedEvents, "/relationship_list/<string:id>/linkedEvents")
API.add_resource(RelationshipLinkedAgents, "/relationship_list/<string:id>/linkedAgents")
API.add_resource(RelationshipLinkedRights, "/relationship_list/<string:id>/linkedRights")
