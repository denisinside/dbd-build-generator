"""The whole pipeline with a scripted model.

Every other test checks one rule in isolation. This one checks that the parts
still fit together: classify -> research loop -> tool dispatch -> structured
generation -> grounding retry -> enrichment -> progress events.
"""

from collections import deque

import pytest
from conftest import killer_build, survivor_build
from langchain_core.messages import AIMessage

import generate_build
from schemas import BuildRequestAnalysis, DbDBuildSchema


class ScriptedStructured:
    """`with_structured_output(...)` result: hands back queued models."""

    def __init__(self, results, prompts):
        self.results = deque(results)
        self.prompts = prompts

    def invoke(self, prompt, config=None):
        self.prompts.append(prompt)
        return self.results.popleft()


class ScriptedLLM:
    """Stands in for ChatOpenRouter across every call in one build."""

    def __init__(self, chat_responses, structured):
        self.chat_responses = deque(chat_responses)
        self.prompts = []
        self.structured = {
            schema: ScriptedStructured(results, self.prompts)
            for schema, results in structured.items()
        }

    def bind_tools(self, _tools):
        return self

    def with_structured_output(self, schema):
        return self.structured[schema]

    def invoke(self, prompt, config=None):
        self.prompts.append(prompt)
        return self.chat_responses.popleft()


class FakeChroma:
    def query(self, query_texts, n_results, where):
        self.last_where = where
        return {
            "documents": [["Sprint Burst makes you sprint. " + "x" * 4000]],
            "metadatas": [[{"entity_name": "Sprint Burst", "category": "perk", "owner": "Meg"}]],
        }


def tool_call(name, args, call_id="call-1"):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


@pytest.fixture
def wired(db, monkeypatch):
    """Pipeline with the database, vector store and model all replaced."""
    monkeypatch.setattr(generate_build, "get_mongo_db", lambda: db)
    monkeypatch.setattr(generate_build, "get_chroma_collection", FakeChroma)
    return db


def run_with(monkeypatch, chat_responses, structured):
    llm = ScriptedLLM(chat_responses, structured)
    monkeypatch.setattr(generate_build, "build_llm", lambda: llm)
    steps = []
    result = generate_build.run_generate_build(
        "Survivor build for fast repairs",
        on_step=lambda stage, detail: steps.append((stage, detail)),
    )
    return result, steps, llm


def accepted(language="English", role="Survivor"):
    return BuildRequestAnalysis(
        is_build_request=True,
        role=role,
        output_language=language,
        rejection_message=None,
    )


def test_a_survivor_prompt_produces_an_enriched_build(wired, monkeypatch):
    build, steps, _ = run_with(
        monkeypatch,
        chat_responses=[
            tool_call("search_dbd_rag", {"query": "repair perks", "role": "Survivor"}),
            tool_call("lookup_mongo_entity", {"entity_name": "Sprint Burst",
                                              "collection_name": "perks"}, "call-2"),
            AIMessage(content="Memo: Meg with repair perks."),
        ],
        structured={
            BuildRequestAnalysis: [accepted()],
            DbDBuildSchema: [DbDBuildSchema.model_validate(survivor_build())],
        },
    )

    assert build["character_name"] == "Meg Thomas"
    assert [perk["name"] for perk in build["perks"]] == [
        "Sprint Burst",
        "Adrenaline",
        "Windows of Opportunity",
        "Déjà Vu",
    ]
    # Enrichment happened: the build carries what the UI renders, not just names.
    assert build["perks"][0]["icon_path"] == "/media/perks/sprint-burst.png"
    assert build["perks"][0]["description"] == "Break into a sprint."
    assert build["character_portrait_url"] == "https://wiki.example/meg.png"
    assert len(build["counter_killers"]) == 5
    assert all(counter["portrait_url"] for counter in build["counter_killers"])
    assert build["item_kits"][0]["item_rarity"] == "Very Rare"


def test_progress_is_reported_for_every_stage(wired, monkeypatch):
    _, steps, _ = run_with(
        monkeypatch,
        chat_responses=[
            tool_call("search_dbd_rag", {"query": "repair perks", "role": "Survivor",
                                         "owner": "Med-Kits"}),
            AIMessage(content="Memo."),
        ],
        structured={
            BuildRequestAnalysis: [accepted()],
            DbDBuildSchema: [DbDBuildSchema.model_validate(survivor_build())],
        },
    )

    stages = [stage for stage, _ in steps]
    assert stages[0] == "classifying"
    assert "research" in stages
    assert "drafting" in stages
    assert stages[-1] == "enriching"

    # The tool call is described in a way a viewer can read.
    details = [detail for _, detail in steps]
    assert any("repair perks" in detail and "Med-Kits" in detail for detail in details)


def test_a_grounding_error_triggers_a_corrected_second_attempt(wired, monkeypatch):
    invented = survivor_build(perks=["Sprint Burst", "Adrenaline", "Déjà Vu", "Made Up Perk"])

    build, steps, llm = run_with(
        monkeypatch,
        chat_responses=[AIMessage(content="Memo.")],
        structured={
            BuildRequestAnalysis: [accepted()],
            DbDBuildSchema: [
                DbDBuildSchema.model_validate(invented),
                DbDBuildSchema.model_validate(survivor_build()),
            ],
        },
    )

    assert build["perks"][3]["name"] == "Déjà Vu"
    # The retry prompt has to name the error, or the model repeats it.
    assert "perk not found: Made Up Perk" in llm.prompts[-1]
    assert ("drafting", "Fixing 1 grounding error(s)") in steps


def test_a_killer_prompt_skips_counter_killers(wired, monkeypatch):
    llm = ScriptedLLM(
        [AIMessage(content="Memo.")],
        {
            BuildRequestAnalysis: [accepted(role="Killer")],
            DbDBuildSchema: [DbDBuildSchema.model_validate(killer_build())],
        },
    )
    monkeypatch.setattr(generate_build, "build_llm", lambda: llm)

    build = generate_build.run_generate_build("Killer build with map pressure")

    assert build["role"] == "Killer"
    assert build["counter_killers"] is None
    assert build["item_kits"][0]["item_name"] is None
    assert build["item_kits"][0]["addons"][0]["rarity"] == "Ultra Rare"


def test_a_rejected_prompt_never_reaches_the_agent(wired, monkeypatch):
    llm = ScriptedLLM(
        [],
        {
            BuildRequestAnalysis: [
                BuildRequestAnalysis(
                    is_build_request=False,
                    role=None,
                    output_language="English",
                    rejection_message="Ask for a Survivor or Killer build.",
                )
            ]
        },
    )
    monkeypatch.setattr(generate_build, "build_llm", lambda: llm)

    result = generate_build.run_generate_build("what is the weather today")

    assert result["error"]["code"] == "invalid_build_request"
    # Only the classifier ran: no chat responses were queued, so reaching the
    # research agent would have raised instead of returning.
    assert len(llm.prompts) == 1


def test_research_stops_when_the_budget_is_spent(wired, monkeypatch):
    """An expired deadline must end the loop instead of burning 12 more calls."""
    llm = ScriptedLLM([AIMessage(content="Partial memo.")], {})
    monkeypatch.setattr(generate_build, "build_llm", lambda: llm)

    spent = generate_build.Deadline(seconds=-1)
    memo = generate_build.run_research_agent(
        "Survivor build",
        "Survivor",
        "English",
        lambda stage, detail: None,
        spent,
    )

    # Straight to the wrap-up call: no research step ran.
    assert memo == "Partial memo."
    assert len(llm.prompts) == 1


def test_a_long_rag_chunk_is_trimmed_before_it_enters_the_context(wired, monkeypatch):
    result = generate_build.search_dbd_rag.invoke(
        {"query": "repair", "role": "Survivor", "category": "perk"}
    )

    assert result.endswith("...")
    assert len(result) < generate_build.RAG_CHUNK_CHARS + 200


def test_the_model_timeout_is_sent_in_milliseconds(monkeypatch):
    """ChatOpenRouter's request_timeout is milliseconds, not seconds.

    Getting this wrong does not merely shorten the timeout: a sub-second
    budget never survives the TLS handshake, and every call hangs instead of
    failing, which takes the whole generator down.
    """
    captured = {}

    class Recorder:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(generate_build, "ChatOpenRouter", Recorder)
    monkeypatch.setattr(generate_build, "OPENROUTER_API_KEY", "test-key")
    generate_build.build_llm()

    assert captured["request_timeout"] == generate_build.LLM_TIMEOUT_SECONDS * 1000
    assert captured["request_timeout"] >= 1000
