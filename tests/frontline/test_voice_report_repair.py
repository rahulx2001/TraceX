"""Text regression from the owner's report. Not a real-audio accuracy study."""
import pytest

from src.agents.base import InteractionContext
from src.agents.intake import IntakeAgent, assess_safety
from src.domains.loader import load_pack


def context():
    return InteractionContext(interaction_id="voice-report-repair", pack=load_pack("automotive_nhtsa"), channel="web_voice")


@pytest.mark.asyncio
async def test_owner_answers_advance_and_ambiguous_year_requires_confirmation():
    ctx = context()
    agent = IntakeAgent(ctx)
    report = "Has got damaged Different panel plus the brake plus the a lot of things has been damaged"
    assert (await agent.run(customer_turn=report))["question"] == "Is anyone hurt?"
    assert "safe location" in (await agent.run(customer_turn="Oh no"))["question"]
    unclear = await agent.run(customer_turn="Loc")
    assert "clear answer" in unclear["question"]
    assert ctx.slots["__safety_pending__"] == "1"
    assert "model year" in (await agent.run(customer_turn="Ah yes I'm in a safe location"))["question"]
    short = await agent.run(customer_turn="11")
    assert "Do you mean model year 2011?" in short["question"]
    assert not ctx.slots.get("entity_1")
    assert (await agent.run(customer_turn="11"))["year_confirmation"]
    assert not ctx.slots.get("entity_1")
    confirmed = await agent.run(customer_turn="yes")
    assert confirmed["extracted"]["entity_1"] == "2011"
    assert ctx.slots["__slot_meta__"]["entity_1"]["source_turn"] == "11"
    assert ctx.slots["__slot_meta__"]["entity_1"]["confirmation_turn"] == "yes"
    assert ctx.slots["description"] == report
    retry = await agent.run(customer_turn="Hello")
    assert "Say just the brand" in retry["question"]
    assert not ctx.slots.get("entity_2")
    assert (await agent.run(customer_turn="Honda"))["extracted"]["entity_2"] == "HONDA"


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["no", "2018", "No, I said 2018"])
async def test_short_year_can_be_rejected_or_corrected(answer):
    ctx = context()
    agent = IntakeAgent(ctx)
    for text in ["My brakes are damaged", "Oh no", "yes", "11"]:
        await agent.run(customer_turn=text)
    await agent.run(customer_turn=answer)
    assert not ctx.slots.get("__year_confirmation__")
    assert ctx.slots.get("entity_1") == (None if answer == "no" else "2018")


@pytest.mark.parametrize("text", ["Oh no, my son has a cut", "Um yes, but I am not in a safe location"])
def test_filler_does_not_hide_safety_contradiction(text):
    question = "Is anyone hurt?" if "son" in text else "Are you in a safe location?"
    result = assess_safety(text, question)
    assert result["contradictory"]
    assert result["polarity"] is None
    for span in result["spans"]:
        assert text[span["start"]:span["end"]] == span["text"]
