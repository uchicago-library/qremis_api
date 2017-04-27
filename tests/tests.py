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
        self.app.blueprint.BLUEPRINT['redis'].flushdb()

    def response_200_json(self, rv):
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        return rj

    def tearDown(self):
        pass

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
        pass

    def test_postEvent(self):
        pass

    def test_postAgent(self):
        pass

    def test_postRights(self):
        pass

    def test_postRelationships(self):
        pass

    def test_getObject(self):
        pass

    def test_getEvent(self):
        pass

    def test_getAgent(self):
        pass

    def test_getRights(self):
        pass

    def test_getRelationships(self):
        pass

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
