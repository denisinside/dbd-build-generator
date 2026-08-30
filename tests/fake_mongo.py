"""Minimal in-memory stand-in for the pymongo Database used by the finders.

The production finders only ever call `db["name"].find({})`, optionally with a
projection they do not depend on, so this is enough to test the whole grounding
layer without a running MongoDB.
"""

import copy


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query=None, projection=None):
        if query:
            raise NotImplementedError("FakeCollection only supports find({})")

        return [copy.deepcopy(document) for document in self.documents]


class FakeDb:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return FakeCollection(self.collections.get(name, []))
