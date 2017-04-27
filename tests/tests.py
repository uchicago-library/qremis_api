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

    def test_manuallyLink(self):
        pass

    def test_implicitLink(self):
        pass

    def test_getObjectLinkedRelationships(self):
        pass

    def test_getEventLinkedRelationships(self):
        pass

    def test_getAgentLinkedRelationships(self):
        pass

    def test_getRightsLinkedRelationships(self):
        pass

    def test_getRelationshipLinkedObjects(self):
        pass

    def test_getRelationshipLinkedEvents(self):
        pass

    def test_getRelationshipLinkedAgents(self):
        pass

    def test_getRelationshipLinkedRights(self):
        pass

if __name__ == '__main__':
    unittest.main()
