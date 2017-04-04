from uuid import uuid4
from json import dumps
import requests
import datetime
from argparse import ArgumentParser

from pyqremis import *

# TODO: Change this from a hacky script to real unit tests

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


def main():
    parser = ArgumentParser()
    parser.add_argument("api_root", type=str)
    args = parser.parse_args()
    obj = make_object()
    event = make_event()
    agent = make_agent()
    rights = make_rights()
    relationship = make_relationship()
    simple_object_resp = requests.post(args.api_root+"/object_list", data={'record': dumps(obj.to_dict())})
    simple_event_resp = requests.post(args.api_root+"/event_list", data={'record': dumps(event.to_dict())})
    simple_agent_resp = requests.post(args.api_root+"/agent_list", data={'record': dumps(agent.to_dict())})
    simple_rights_resp = requests.post(args.api_root+"/rights_list", data={'record': dumps(rights.to_dict())})
    simple_relationship_resp = requests.post(args.api_root+"/relationship_list", data={'record': dumps(relationship.to_dict())})

    simple_responses = [simple_object_resp, simple_event_resp,
                        simple_agent_resp, simple_rights_resp,
                        simple_relationship_resp]

    for x in simple_responses:
        x.raise_for_status()
        x.json()

    assert(
        requests.get(args.api_root+simple_object_resp.json()['_link']).json() == obj.to_dict()
    )

    assert(
        requests.get(args.api_root+simple_agent_resp.json()['_link']).json() == agent.to_dict()
    )

    assert(
        requests.get(args.api_root+simple_event_resp.json()['_link']).json() == event.to_dict()
    )

    assert(
        requests.get(args.api_root+simple_rights_resp.json()['_link']).json() == rights.to_dict()
    )

    assert(
        requests.get(args.api_root+simple_relationship_resp.json()['_link']).json() == relationship.to_dict()
    )

    obj_links_resp = requests.get(args.api_root+simple_object_resp.json()['_link']+'/linkedRelationships')
    obj_links_resp.raise_for_status()
    obj_links_resp.json()

    event_links_resp = requests.get(args.api_root+simple_event_resp.json()['_link']+'/linkedRelationships')
    event_links_resp.raise_for_status()
    event_links_resp.json()

    agent_links_resp = requests.get(args.api_root+simple_agent_resp.json()['_link']+'/linkedRelationships')
    agent_links_resp.raise_for_status()
    agent_links_resp.json()

    rights_links_resp = requests.get(args.api_root+simple_rights_resp.json()['_link']+'/linkedRelationships')
    rights_links_resp.raise_for_status()
    rights_links_resp.json()

    relationship_links_resp1 = requests.get(args.api_root+simple_relationship_resp.json()['_link']+'/linkedObjects')
    relationship_links_resp1.raise_for_status()
    relationship_links_resp1.json()

    relationship_links_resp2 = requests.get(args.api_root+simple_relationship_resp.json()['_link']+'/linkedEvents')
    relationship_links_resp2.raise_for_status()
    relationship_links_resp2.json()

    relationship_links_resp3 = requests.get(args.api_root+simple_relationship_resp.json()['_link']+'/linkedAgents')
    relationship_links_resp3.raise_for_status()
    relationship_links_resp3.json()

    relationship_links_resp4 = requests.get(args.api_root+simple_relationship_resp.json()['_link']+'/linkedRights')
    relationship_links_resp4.raise_for_status()
    relationship_links_resp4.json()

    # TODO: Change these from prints to asserts
    link_obj_resp = requests.post(
        args.api_root+simple_object_resp.json()['_link']+'/linkedRelationships',
        data={
            "relationship_id": relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        }
    )
    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/object_list" + "/" + obj.get_objectIdentifier()[0].get_objectIdentifierValue()
            ).json(),
            indent=4
        )
    )
    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" + relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
            ).json(), indent=4
        )
    )

    print("###############")
    link_event_resp = requests.post(
        args.api_root+simple_event_resp.json()['_link']+'/linkedRelationships',
        data={
            "relationship_id": relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        }
    )
    print(
        dumps(
            requests.get(
                args.api_root+"/event_list" + "/" + event.get_eventIdentifier()[0].get_eventIdentifierValue()
            ).json(),
            indent=4
        )
    )
    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" + relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
            ).json(), indent=4
        )
    )

    print("###############")
    link_agent_resp = requests.post(
        args.api_root+simple_agent_resp.json()['_link']+'/linkedRelationships',
        data={
            "relationship_id": relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        }
    )
    print(
        dumps(
            requests.get(
                args.api_root+"/agent_list" + "/" + agent.get_agentIdentifier()[0].get_agentIdentifierValue()
            ).json(),
            indent=4
        )
    )
    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" + relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
            ).json(), indent=4
        )
    )

    print("###############")
    link_rights_resp = requests.post(
        args.api_root+simple_rights_resp.json()['_link']+'/linkedRelationships',
        data={
            "relationship_id": relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
        }
    )
    print(
        dumps(
            requests.get(
                args.api_root+"/rights_list" + "/" + rights.get_rightsIdentifier()[0].get_rightsIdentifierValue()
            ).json(),
            indent=4
        )
    )
    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" + relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue()
            ).json(), indent=4
        )
    )

    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" +
                relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue() +
                "/linkedObjects").json(),
            indent=4
        )
    )

    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" +
                relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue() +
                "/linkedEvents").json(),
            indent=4
        )
    )

    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" +
                relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue() +
                "/linkedAgents").json(),
            indent=4
        )
    )

    print("###############")
    print(
        dumps(
            requests.get(
                args.api_root+"/relationship_list" + "/" +
                relationship.get_relationshipIdentifier()[0].get_relationshipIdentifierValue() +
                "/linkedRights").json(),
            indent=4
        )
    )
if __name__ == "__main__":
    main()
