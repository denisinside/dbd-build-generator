"""Minimal in-memory stand-in for the pymongo Database used by the finders.

Supports only what the finders actually use: equality on a field (with Mongo's
array semantics, so `{"search_keys": "x"}` matches a document whose
`search_keys` list contains "x"), `$in`, and projections it can ignore.
"""

import copy


def field_matches(stored, expected):
    values = stored if isinstance(stored, list) else [stored]

    if isinstance(expected, dict):
        return bool(set(values) & set(expected["$in"]))

    return expected in values


def document_matches(document, query):
    return all(field_matches(document.get(field), expected) for field, expected in query.items())


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query=None, projection=None):
        return [
            copy.deepcopy(document)
            for document in self.documents
            if document_matches(document, query or {})
        ]

    def find_one(self, query=None, projection=None):
        return next(iter(self.find(query, projection)), None)


class FakeDb:
    def __init__(self, collections):
        for documents in collections.values():
            for index, document in enumerate(documents):
                document.setdefault("_id", index)

        self.collections = collections

    def __getitem__(self, name):
        return FakeCollection(self.collections.get(name, []))
