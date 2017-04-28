from uuid import uuid4
import datetime
import unittest
import redis
import json

import qremis_api

from pyqremis import *


def make_object():
    objIdentifier = ObjectIdentifier(objectIdentifierType="uuid", objectIdentifierValue=uuid4().hex)
    objChar = ObjectCharacteristics(Format(FormatDesignation(formatName="foo")))
    obj = Object(objIdentifier, objChar, objectCategory="file")
    return obj


def make_relationship():
    relIdentifier = RelationshipIdentifier(
        relationshipIdentifierType="uuid",
        relationshipIdentifierValue=uuid4().hex
    )
    rel = Relationship(relIdentifier, relationshipType="link", relationshipSubType="simple")
    return rel


def make_agent():
    agentIdentifier = AgentIdentifier(agentIdentifierType="uuid", agentIdentifierValue=uuid4().hex)
    return Agent(agentIdentifier)


def make_rights():
    rightsIdentifier = RightsIdentifier(rightsIdentifierType="uuid", rightsIdentifierValue=uuid4().hex)
    return Rights(rightsIdentifier)


def make_event():
    eventIdentifier = EventIdentifier(eventIdentifierType="uuid", eventIdentifierValue=uuid4().hex)
    eventType = "testing"
    eventDateTime = str(datetime.datetime.now())
    return Event(eventIdentifier, eventType=eventType, eventDateTime=eventDateTime)


def add_linkingRelationshipIdentifier(entity, rel_id):
    entity.add_linkingRelationshipIdentifier(
        LinkingRelationshipIdentifier(
            linkingRelationshipIdentifierType="uuid",
            linkingRelationshipIdentifierValue=rel_id
        )
    )


class AddEntitiesTests(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        qremis_api.app.config['TESTING'] = True
        self.app = qremis_api.app.test_client()
        qremis_api.blueprint.BLUEPRINT.config['redis'] = redis.StrictRedis(
            host='localhost',
            port=6379,
            db=0
        )

    def tearDown(self):
        qremis_api.blueprint.BLUEPRINT.config['redis'].flushdb()

    def response_200_json(self, rv):
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        return rj

    def test_getRoot(self):
        rv = self.app.get("/")
        rj = self.response_200_json(rv)

    def test_getObjectList(self):
        rv = self.app.get("/object_list")
        rj = self.response_200_json(rv)

    def test_getEventList(self):
        rv = self.app.get("/event_list")
        rj = self.response_200_json(rv)

    def test_getAgentList(self):
        rv = self.app.get("/agent_list")
        rj = self.response_200_json(rv)

    def test_getRightsList(self):
        rv = self.app.get("/rights_list")
        rj = self.response_200_json(rv)

    def test_getRelationshipList(self):
        rv = self.app.get("/relationship_list")
        rj = self.response_200_json(rv)

    def test_postObject(self):
        entity = make_object()
        entity_json = entity.to_dict()
        rv = self.app.post("/object_list", data={"record": json.dumps(entity_json)})
        rj = self.response_200_json(rv)

    def test_postEvent(self):
        entity = make_event()
        entity_json = entity.to_dict()
        rv = self.app.post("/event_list", data={"record": json.dumps(entity_json)})
        rj = self.response_200_json(rv)

    def test_postAgent(self):
        entity = make_agent()
        entity_json = entity.to_dict()
        rv = self.app.post("/agent_list", data={"record": json.dumps(entity_json)})
        rj = self.response_200_json(rv)

    def test_postRights(self):
        entity = make_rights()
        entity_json = entity.to_dict()
        rv = self.app.post("/rights_list", data={"record": json.dumps(entity_json)})
        rj = self.response_200_json(rv)

    def test_postRelationship(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        rv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        rj = self.response_200_json(rv)

    def test_getObject(self):
        entity = make_object()
        entity_json = entity.to_dict()
        prv = self.app.post("/object_list", data={"record": json.dumps(entity_json)})
        prj = self.response_200_json(prv)
        grv = self.app.get("/object_list/{}".format(prj['id']))
        grj = self.response_200_json(grv)
        self.assertEqual(entity_json, grj)

    def test_getEvent(self):
        entity = make_event()
        entity_json = entity.to_dict()
        prv = self.app.post("/event_list", data={"record": json.dumps(entity_json)})
        prj = self.response_200_json(prv)
        grv = self.app.get("/event_list/{}".format(prj['id']))
        grj = self.response_200_json(grv)
        self.assertEqual(entity_json, grj)

    def test_getAgent(self):
        entity = make_agent()
        entity_json = entity.to_dict()
        prv = self.app.post("/agent_list", data={"record": json.dumps(entity_json)})
        prj = self.response_200_json(prv)
        grv = self.app.get("/agent_list/{}".format(prj['id']))
        grj = self.response_200_json(grv)
        self.assertEqual(entity_json, grj)

    def test_getRights(self):
        entity = make_rights()
        entity_json = entity.to_dict()
        prv = self.app.post("/rights_list", data={"record": json.dumps(entity_json)})
        prj = self.response_200_json(prv)
        grv = self.app.get("/rights_list/{}".format(prj['id']))
        grj = self.response_200_json(grv)
        self.assertEqual(entity_json, grj)

    def test_getRelationship(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        prv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        prj = self.response_200_json(prv)
        grv = self.app.get("/relationship_list/{}".format(prj['id']))
        grj = self.response_200_json(grv)
        self.assertEqual(entity_json, grj)

    def test_getNonExistantObject(self):
        grv = self.app.get("/object_list/{}".format(uuid4().hex))
        self.assertEqual(grv.status_code, 404)

    def test_getNonExistantEvent(self):
        grv = self.app.get("/event_list/{}".format(uuid4().hex))
        self.assertEqual(grv.status_code, 404)

    def test_getNonExistantAgent(self):
        grv = self.app.get("/agent_list/{}".format(uuid4().hex))
        self.assertEqual(grv.status_code, 404)

    def test_getNonExistantRights(self):
        grv = self.app.get("/rights_list/{}".format(uuid4().hex))
        self.assertEqual(grv.status_code, 404)

    def test_getNonExistantRelationship(self):
        grv = self.app.get("/relationship_list/{}".format(uuid4().hex))
        self.assertEqual(grv.status_code, 404)

    def test_getObjectListPagination(self):
        entities = []
        for _ in range(1234):
            entities.append(make_object())
        entities_ids = [x.get_objectIdentifier()[0].get_objectIdentifierValue() for x in entities]
        self.assertEqual(len(entities_ids), len(set(entities_ids)))
        self.assertEqual(len(entities_ids), 1234)
        entities_dicts = [x.to_dict() for x in entities]
        for x in entities_dicts:
            self.app.post("/object_list", data={"record": json.dumps(x)})
        comp_entities_ids = []
        next_cursor = "0"
        while next_cursor:
            rv = self.app.get("/object_list", data={"cursor": next_cursor, "limit": 200})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['object_list']:
                comp_entities_ids.append(x['id'])
        self.assertEqual(len(comp_entities_ids), 1234)
        self.assertEqual(len(comp_entities_ids), len(set(comp_entities_ids)))
        for x in comp_entities_ids:
            self.assertIn(x, entities_ids)

    def test_getEventListPagination(self):
        entities = []
        for _ in range(1234):
            entities.append(make_event())
        entities_ids = [x.get_eventIdentifier()[0].get_eventIdentifierValue() for x in entities]
        self.assertEqual(len(entities_ids), len(set(entities_ids)))
        self.assertEqual(len(entities_ids), 1234)
        entities_dicts = [x.to_dict() for x in entities]
        for x in entities_dicts:
            self.app.post("/event_list", data={"record": json.dumps(x)})
        comp_entities_ids = []
        next_cursor = "0"
        while next_cursor:
            rv = self.app.get("/event_list", data={"cursor": next_cursor, "limit": 200})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['event_list']:
                comp_entities_ids.append(x['id'])
        self.assertEqual(len(comp_entities_ids), 1234)
        self.assertEqual(len(comp_entities_ids), len(set(comp_entities_ids)))
        for x in comp_entities_ids:
            self.assertIn(x, entities_ids)

    def test_getAgentListPagination(self):
        entities = []
        for _ in range(1234):
            entities.append(make_agent())
        entities_ids = [x.get_agentIdentifier()[0].get_agentIdentifierValue() for x in entities]
        self.assertEqual(len(entities_ids), len(set(entities_ids)))
        self.assertEqual(len(entities_ids), 1234)
        entities_dicts = [x.to_dict() for x in entities]
        for x in entities_dicts:
            self.app.post("/agent_list", data={"record": json.dumps(x)})
        comp_entities_ids = []
        next_cursor = "0"
        while next_cursor:
            rv = self.app.get("/agent_list", data={"cursor": next_cursor, "limit": 200})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['agent_list']:
                comp_entities_ids.append(x['id'])
        self.assertEqual(len(comp_entities_ids), 1234)
        self.assertEqual(len(comp_entities_ids), len(set(comp_entities_ids)))
        for x in comp_entities_ids:
            self.assertIn(x, entities_ids)

    def test_getRightsListPagination(self):
        entities = []
        for _ in range(1234):
            entities.append(make_rights())
        entities_ids = [x.get_rightsIdentifier()[0].get_rightsIdentifierValue() for x in entities]
        self.assertEqual(len(entities_ids), len(set(entities_ids)))
        self.assertEqual(len(entities_ids), 1234)
        entities_dicts = [x.to_dict() for x in entities]
        for x in entities_dicts:
            self.app.post("/rights_list", data={"record": json.dumps(x)})
        comp_entities_ids = []
        next_cursor = "0"
        while next_cursor:
            rv = self.app.get("/rights_list", data={"cursor": next_cursor, "limit": 200})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['rights_list']:
                comp_entities_ids.append(x['id'])
        self.assertEqual(len(comp_entities_ids), 1234)
        self.assertEqual(len(comp_entities_ids), len(set(comp_entities_ids)))
        for x in comp_entities_ids:
            self.assertIn(x, entities_ids)

    def test_getRelationshipListPagination(self):
        entities = []
        for _ in range(1234):
            entities.append(make_relationship())
        entities_ids = [x.get_relationshipIdentifier()[0].get_relationshipIdentifierValue() for x in entities]
        self.assertEqual(len(entities_ids), len(set(entities_ids)))
        self.assertEqual(len(entities_ids), 1234)
        entities_dicts = [x.to_dict() for x in entities]
        for x in entities_dicts:
            self.app.post("/relationship_list", data={"record": json.dumps(x)})
        comp_entities_ids = []
        next_cursor = "0"
        while next_cursor:
            rv = self.app.get("/relationship_list", data={"cursor": next_cursor, "limit": 200})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['relationship_list']:
                comp_entities_ids.append(x['id'])
        self.assertEqual(len(comp_entities_ids), 1234)
        self.assertEqual(len(comp_entities_ids), len(set(comp_entities_ids)))
        for x in comp_entities_ids:
            self.assertIn(x, entities_ids)

    def test_manuallyLinkObject(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        obj = make_object()
        obj_identifier = obj.get_objectIdentifier()[0].get_objectIdentifierValue()
        obj_json = obj.to_dict()
        oprv = self.app.post("/object_list", data={"record": json.dumps(obj_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/object_list/{}/linkedRelationships".format(obj_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        obj.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingObjectIdentifier(
            LinkingObjectIdentifier(
                linkingObjectIdentifierType="uuid",
                linkingObjectIdentifierValue=obj_identifier
            )
        )

        ogrv = self.app.get("/object_list/{}".format(obj_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, obj.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkEvent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        event = make_event()
        event_identifier = event.get_eventIdentifier()[0].get_eventIdentifierValue()
        event_json = event.to_dict()
        oprv = self.app.post("/event_list", data={"record": json.dumps(event_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/event_list/{}/linkedRelationships".format(event_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        event.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingEventIdentifier(
            LinkingEventIdentifier(
                linkingEventIdentifierType="uuid",
                linkingEventIdentifierValue=event_identifier
            )
        )

        ogrv = self.app.get("/event_list/{}".format(event_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, event.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkAgent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        agent = make_agent()
        agent_identifier = agent.get_agentIdentifier()[0].get_agentIdentifierValue()
        agent_json = agent.to_dict()
        oprv = self.app.post("/agent_list", data={"record": json.dumps(agent_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/agent_list/{}/linkedRelationships".format(agent_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        agent.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingAgentIdentifier(
            LinkingAgentIdentifier(
                linkingAgentIdentifierType="uuid",
                linkingAgentIdentifierValue=agent_identifier
            )
        )

        ogrv = self.app.get("/agent_list/{}".format(agent_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, agent.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkRights(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        rights = make_rights()
        rights_identifier = rights.get_rightsIdentifier()[0].get_rightsIdentifierValue()
        rights_json = rights.to_dict()
        oprv = self.app.post("/rights_list", data={"record": json.dumps(rights_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/rights_list/{}/linkedRelationships".format(rights_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        rights.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingRightsIdentifier(
            LinkingRightsIdentifier(
                linkingRightsIdentifierType="uuid",
                linkingRightsIdentifierValue=rights_identifier
            )
        )

        ogrv = self.app.get("/rights_list/{}".format(rights_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, rights.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkRelationshipToObject(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        obj = make_object()
        obj_identifier = obj.get_objectIdentifier()[0].get_objectIdentifierValue()
        obj_json = obj.to_dict()
        oprv = self.app.post("/object_list", data={"record": json.dumps(obj_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/relationship_list/{}/linkedObjects".format(relationship_id),
                              data={"object_id": obj_identifier})
        oprrj = self.response_200_json(oprrv)

        obj.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingObjectIdentifier(
            LinkingObjectIdentifier(
                linkingObjectIdentifierType="uuid",
                linkingObjectIdentifierValue=obj_identifier
            )
        )

        ogrv = self.app.get("/object_list/{}".format(obj_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, obj.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkRelationshipToEvent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        event = make_event()
        event_identifier = event.get_eventIdentifier()[0].get_eventIdentifierValue()
        event_json = event.to_dict()
        oprv = self.app.post("/event_list", data={"record": json.dumps(event_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/relationship_list/{}/linkedEvents".format(relationship_id),
                              data={"event_id": event_identifier})
        oprrj = self.response_200_json(oprrv)

        event.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingEventIdentifier(
            LinkingEventIdentifier(
                linkingEventIdentifierType="uuid",
                linkingEventIdentifierValue=event_identifier
            )
        )

        ogrv = self.app.get("/event_list/{}".format(event_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, event.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkRelationshipToAgent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        agent = make_agent()
        agent_identifier = agent.get_agentIdentifier()[0].get_agentIdentifierValue()
        agent_json = agent.to_dict()
        oprv = self.app.post("/agent_list", data={"record": json.dumps(agent_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/relationship_list/{}/linkedAgents".format(relationship_id),
                              data={"agent_id": agent_identifier})
        oprrj = self.response_200_json(oprrv)

        agent.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingAgentIdentifier(
            LinkingAgentIdentifier(
                linkingAgentIdentifierType="uuid",
                linkingAgentIdentifierValue=agent_identifier
            )
        )

        ogrv = self.app.get("/agent_list/{}".format(agent_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, agent.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_manuallyLinkRelationshipToRights(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        rights = make_rights()
        rights_identifier = rights.get_rightsIdentifier()[0].get_rightsIdentifierValue()
        rights_json = rights.to_dict()
        oprv = self.app.post("/rights_list", data={"record": json.dumps(rights_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/relationship_list/{}/linkedRights".format(relationship_id),
                              data={"rights_id": rights_identifier})
        oprrj = self.response_200_json(oprrv)

        rights.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingRightsIdentifier(
            LinkingRightsIdentifier(
                linkingRightsIdentifierType="uuid",
                linkingRightsIdentifierValue=rights_identifier
            )
        )

        ogrv = self.app.get("/rights_list/{}".format(rights_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, rights.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_implicitLinkObject(self):
        entity = make_object()
        entity_id = entity.get_objectIdentifier()[0].get_objectIdentifierValue()

        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )
        relationship.add_linkingObjectIdentifier(
            LinkingObjectIdentifier(
                linkingObjectIdentifierType="uuid",
                linkingObjectIdentifierValue=entity_id
            )
        )

        self.response_200_json(
            self.app.post("/object_list", data={"record": json.dumps(entity.to_dict())})
        )
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )

        entity.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        self.assertEqual(
            self.response_200_json(self.app.get("/object_list/{}".format(entity_id))),
            entity.to_dict()
        )
        self.assertTrue(
            self.response_200_json(self.app.get("/relationship_list/{}".format(relationship_id))) == \
            relationship.to_dict()
        )

    def test_implicitLinkEvent(self):
        entity = make_event()
        entity_id = entity.get_eventIdentifier()[0].get_eventIdentifierValue()

        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )
        relationship.add_linkingEventIdentifier(
            LinkingEventIdentifier(
                linkingEventIdentifierType="uuid",
                linkingEventIdentifierValue=entity_id
            )
        )

        self.response_200_json(
            self.app.post("/event_list", data={"record": json.dumps(entity.to_dict())})
        )
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )

        entity.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        self.assertEqual(
            self.response_200_json(self.app.get("/event_list/{}".format(entity_id))),
            entity.to_dict()
        )
        self.assertTrue(
            self.response_200_json(self.app.get("/relationship_list/{}".format(relationship_id))) == \
            relationship.to_dict()
        )

    def test_implicitLinkAgent(self):
        entity = make_agent()
        entity_id = entity.get_agentIdentifier()[0].get_agentIdentifierValue()

        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )
        relationship.add_linkingAgentIdentifier(
            LinkingAgentIdentifier(
                linkingAgentIdentifierType="uuid",
                linkingAgentIdentifierValue=entity_id
            )
        )

        self.response_200_json(
            self.app.post("/agent_list", data={"record": json.dumps(entity.to_dict())})
        )
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )

        entity.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        self.assertEqual(
            self.response_200_json(self.app.get("/agent_list/{}".format(entity_id))),
            entity.to_dict()
        )
        self.assertTrue(
            self.response_200_json(self.app.get("/relationship_list/{}".format(relationship_id))) == \
            relationship.to_dict()
        )

    def test_implicitLinkRights(self):
        entity = make_rights()
        entity_id = entity.get_rightsIdentifier()[0].get_rightsIdentifierValue()

        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )
        relationship.add_linkingRightsIdentifier(
            LinkingRightsIdentifier(
                linkingRightsIdentifierType="uuid",
                linkingRightsIdentifierValue=entity_id
            )
        )

        self.response_200_json(
            self.app.post("/rights_list", data={"record": json.dumps(entity.to_dict())})
        )
        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
        )

        entity.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        self.assertEqual(
            self.response_200_json(self.app.get("/rights_list/{}".format(entity_id))),
            entity.to_dict()
        )
        self.assertTrue(
            self.response_200_json(self.app.get("/relationship_list/{}".format(relationship_id))) == \
            relationship.to_dict()
        )

    def test_implicitLinkRelationshipToObject(self):
        target_relationship = make_relationship()
        target_relationship_id = target_relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()

        obj = make_object()
        obj_identifier = obj.get_objectIdentifier()[0].get_objectIdentifierValue()

        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(target_relationship.to_dict())})
        )

        obj.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=target_relationship_id
            )
        )
        self.response_200_json(
            self.app.post("/object_list", data={"record": json.dumps(obj.to_dict())})
        )

        target_relationship.add_linkingObjectIdentifier(
            LinkingObjectIdentifier(
                linkingObjectIdentifierType="uuid",
                linkingObjectIdentifierValue=obj_identifier
            )
        )

        self.assertEqual(
            self.response_200_json(
                self.app.get("/relationship_list/{}".format(target_relationship_id))
            ),
            target_relationship.to_dict()
        )

    def test_implicitLinkRelationshipToEvent(self):
        target_relationship = make_relationship()
        target_relationship_id = target_relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()

        event = make_event()
        event_identifier = event.get_eventIdentifier()[0].get_eventIdentifierValue()

        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(target_relationship.to_dict())})
        )

        event.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=target_relationship_id
            )
        )
        self.response_200_json(
            self.app.post("/event_list", data={"record": json.dumps(event.to_dict())})
        )

        target_relationship.add_linkingEventIdentifier(
            LinkingEventIdentifier(
                linkingEventIdentifierType="uuid",
                linkingEventIdentifierValue=event_identifier
            )
        )

        self.assertEqual(
            self.response_200_json(
                self.app.get("/relationship_list/{}".format(target_relationship_id))
            ),
            target_relationship.to_dict()
        )

    def test_implicitLinkRelationshipToAgent(self):
        target_relationship = make_relationship()
        target_relationship_id = target_relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()

        agent = make_agent()
        agent_identifier = agent.get_agentIdentifier()[0].get_agentIdentifierValue()

        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(target_relationship.to_dict())})
        )

        agent.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=target_relationship_id
            )
        )
        self.response_200_json(
            self.app.post("/agent_list", data={"record": json.dumps(agent.to_dict())})
        )

        target_relationship.add_linkingAgentIdentifier(
            LinkingAgentIdentifier(
                linkingAgentIdentifierType="uuid",
                linkingAgentIdentifierValue=agent_identifier
            )
        )

        self.assertEqual(
            self.response_200_json(
                self.app.get("/relationship_list/{}".format(target_relationship_id))
            ),
            target_relationship.to_dict()
        )

    def test_implicitLinkRelationshipToRights(self):
        target_relationship = make_relationship()
        target_relationship_id = target_relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()

        rights = make_rights()
        rights_identifier = rights.get_rightsIdentifier()[0].get_rightsIdentifierValue()

        self.response_200_json(
            self.app.post("/relationship_list", data={"record": json.dumps(target_relationship.to_dict())})
        )

        rights.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=target_relationship_id
            )
        )
        self.response_200_json(
            self.app.post("/rights_list", data={"record": json.dumps(rights.to_dict())})
        )

        target_relationship.add_linkingRightsIdentifier(
            LinkingRightsIdentifier(
                linkingRightsIdentifierType="uuid",
                linkingRightsIdentifierValue=rights_identifier
            )
        )

        self.assertEqual(
            self.response_200_json(
                self.app.get("/relationship_list/{}".format(target_relationship_id))
            ),
            target_relationship.to_dict()
        )

    def test_getObjectLinkedRelationships(self):
        entity = make_object()
        entity_json = entity.to_dict()
        eprv = self.app.post("/object_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/object_list/{}/linkedRelationships".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getEventLinkedRelationships(self):
        entity = make_event()
        entity_json = entity.to_dict()
        eprv = self.app.post("/event_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/event_list/{}/linkedRelationships".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getAgentLinkedRelationships(self):
        entity = make_agent()
        entity_json = entity.to_dict()
        eprv = self.app.post("/agent_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/agent_list/{}/linkedRelationships".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getRightsLinkedRelationships(self):
        entity = make_rights()
        entity_json = entity.to_dict()
        eprv = self.app.post("/rights_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/rights_list/{}/linkedRelationships".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getRelationshipLinkedObjects(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        eprv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/relationship_list/{}/linkedObjects".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getRelationshipLinkedEvents(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        eprv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/relationship_list/{}/linkedEvents".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getRelationshipLinkedAgents(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        eprv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/relationship_list/{}/linkedAgents".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getRelationshipLinkedRights(self):
        entity = make_relationship()
        entity_json = entity.to_dict()
        eprv = self.app.post("/relationship_list", data={"record": json.dumps(entity_json)})
        eprj = self.response_200_json(eprv)
        rv = self.app.get("/relationship_list/{}/linkedRights".format(eprj['id']))
        rj = self.response_200_json(rv)

    def test_getSparseObject(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        obj = make_object()
        obj_identifier = obj.get_objectIdentifier()[0].get_objectIdentifierValue()
        obj_json = obj.to_dict()
        oprv = self.app.post("/object_list", data={"record": json.dumps(obj_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/object_list/{}/linkedRelationships".format(obj_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        sogrv = self.app.get("/object_list/{}/sparse".format(obj_identifier))
        sogrj = self.response_200_json(sogrv)
        self.assertEqual(sogrj, obj.to_dict())

        srgrv = self.app.get("/relationship_list/{}/sparse".format(relationship_id))
        srgrj = self.response_200_json(srgrv)
        self.assertEqual(srgrj, relationship.to_dict())

        obj.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingObjectIdentifier(
            LinkingObjectIdentifier(
                linkingObjectIdentifierType="uuid",
                linkingObjectIdentifierValue=obj_identifier
            )
        )

        ogrv = self.app.get("/object_list/{}".format(obj_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, obj.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_getSparseEvent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        event = make_event()
        event_identifier = event.get_eventIdentifier()[0].get_eventIdentifierValue()
        event_json = event.to_dict()
        oprv = self.app.post("/event_list", data={"record": json.dumps(event_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/event_list/{}/linkedRelationships".format(event_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        sogrv = self.app.get("/event_list/{}/sparse".format(event_identifier))
        sogrj = self.response_200_json(sogrv)
        self.assertEqual(sogrj, event.to_dict())

        srgrv = self.app.get("/relationship_list/{}/sparse".format(relationship_id))
        srgrj = self.response_200_json(srgrv)
        self.assertEqual(srgrj, relationship.to_dict())

        event.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingEventIdentifier(
            LinkingEventIdentifier(
                linkingEventIdentifierType="uuid",
                linkingEventIdentifierValue=event_identifier
            )
        )

        ogrv = self.app.get("/event_list/{}".format(event_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, event.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_getSparseAgent(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        agent = make_agent()
        agent_identifier = agent.get_agentIdentifier()[0].get_agentIdentifierValue()
        agent_json = agent.to_dict()
        oprv = self.app.post("/agent_list", data={"record": json.dumps(agent_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/agent_list/{}/linkedRelationships".format(agent_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        sogrv = self.app.get("/agent_list/{}/sparse".format(agent_identifier))
        sogrj = self.response_200_json(sogrv)
        self.assertEqual(sogrj, agent.to_dict())

        srgrv = self.app.get("/relationship_list/{}/sparse".format(relationship_id))
        srgrj = self.response_200_json(srgrv)
        self.assertEqual(srgrj, relationship.to_dict())

        agent.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingAgentIdentifier(
            LinkingAgentIdentifier(
                linkingAgentIdentifierType="uuid",
                linkingAgentIdentifierValue=agent_identifier
            )
        )

        ogrv = self.app.get("/agent_list/{}".format(agent_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, agent.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_getSparseRights(self):
        relationship = make_relationship()
        relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        relationship_json = relationship.to_dict()
        rprv = self.app.post("/relationship_list", data={"record": json.dumps(relationship_json)})
        rprj = self.response_200_json(rprv)

        rights = make_rights()
        rights_identifier = rights.get_rightsIdentifier()[0].get_rightsIdentifierValue()
        rights_json = rights.to_dict()
        oprv = self.app.post("/rights_list", data={"record": json.dumps(rights_json)})
        oprj = self.response_200_json(oprv)
        oprrv = self.app.post("/rights_list/{}/linkedRelationships".format(rights_identifier),
                              data={"relationship_id": relationship_id})
        oprrj = self.response_200_json(oprrv)

        sogrv = self.app.get("/rights_list/{}/sparse".format(rights_identifier))
        sogrj = self.response_200_json(sogrv)
        self.assertEqual(sogrj, rights.to_dict())

        srgrv = self.app.get("/relationship_list/{}/sparse".format(relationship_id))
        srgrj = self.response_200_json(srgrv)
        self.assertEqual(srgrj, relationship.to_dict())

        rights.add_linkingRelationshipIdentifier(
            LinkingRelationshipIdentifier(
                linkingRelationshipIdentifierType="uuid",
                linkingRelationshipIdentifierValue=relationship_id
            )
        )
        relationship.add_linkingRightsIdentifier(
            LinkingRightsIdentifier(
                linkingRightsIdentifierType="uuid",
                linkingRightsIdentifierValue=rights_identifier
            )
        )

        ogrv = self.app.get("/rights_list/{}".format(rights_identifier))
        ogrj = self.response_200_json(ogrv)
        self.assertEqual(ogrj, rights.to_dict())

        rgrv = self.app.get("relationship_list/{}".format(relationship_id))
        rgrj = self.response_200_json(rgrv)
        self.assertEqual(rgrj, relationship.to_dict())

    def test_linkedRelationshipsPagination(self):
        event = make_event()
        event_id = event.get_eventIdentifier()[0].get_eventIdentifierValue()
        eprj = self.response_200_json(
            self.app.post("/event_list", data={"record": json.dumps(event.to_dict())})
        )
        relationship_ids = []
        for _ in range(1234):
            relationship = make_relationship()
            self.response_200_json(
                self.app.post("/relationship_list", data={"record": json.dumps(relationship.to_dict())})
            )
            relationship_id = relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
            relationship_ids.append(relationship_id)
            self.response_200_json(
                self.app.post("/event_list/{}/linkedRelationships".format(event_id), data={"relationship_id": relationship_id})
            )
        cursor = "0"
        comp_rel_ids = []
        while cursor:
            rj = self.response_200_json(
                self.app.get("/event_list/{}/linkedRelationships".format(event_id), data={"cursor": cursor, "limit": 200})
            )
            cursor = rj['pagination']['next_cursor']
            for x in rj['linkingRelationshipIdentifier_list']:
                comp_rel_ids.append(x['id'])
        self.assertEqual(len(comp_rel_ids), 1234)
        self.assertEqual(len(comp_rel_ids), len(set(comp_rel_ids)))
        for x in comp_rel_ids:
            self.assertIn(x, relationship_ids)


if __name__ == '__main__':
    unittest.main()
