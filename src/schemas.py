from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# Single source for the icon set. `generate_build.py` imports this list
# (rather than keeping its own copy) so a Python-side change can't drift; the
# Lucide component map in frontend/lib/icon-registry.tsx still has to be kept
# in sync by hand, checked by tests/test_icons_sync.py.
ALLOWED_ICONS = [
    "book",
    "trophy",
    "eye",
    "wrench",
    "zap",
    "gauge",
    "footprints",
    "cog",
    "target",
    "users",
    "shield-alert",
    "timer",
    "sparkles",
    "heart",
    "radar",
    "ghost",
]

# A Literal needs its members spelled out, so this can't be `Literal[*ALLOWED_ICONS]`
# on the nose everywhere (Pydantic wants a real Literal type) — built from the
# same list instead of retyped, so the two can't drift.
LucideIcon = Literal[tuple(ALLOWED_ICONS)]


# The classifier's language choice is interpolated straight into the research
# system prompt, so it must not be free text coming from a model that just read
# the user's message. A Literal makes structured output pick from this list and
# closes that injection path. Russian is left out deliberately.
OutputLanguage = Literal[
    "English",
    "Ukrainian",
    "Polish",
    "German",
    "French",
    "Spanish",
    "Portuguese",
    "Italian",
    "Turkish",
    "Czech",
    "Japanese",
    "Korean",
    "Chinese",
]


class BuildRequestAnalysis(BaseModel):
    is_build_request: bool = Field(
        description="True only when the user clearly asks for a DbD build"
    )
    role: Optional[Literal["Survivor", "Killer"]] = Field(
        default=None,
        description="Requested DbD role; null when missing or unclear",
    )
    output_language: OutputLanguage = Field(
        description="Language to use for generated prose; English when unsupported"
    )
    rejection_message: Optional[str] = Field(
        default=None,
        description="Short user-facing error when the request is rejected",
    )

    @model_validator(mode="after")
    def validate_request_analysis(self):
        # "Make me the strongest build" is a build request with no role, and
        # models answer it with is_build_request=True plus a rejection message
        # explaining the role is missing. Raising here turned that ordinary
        # prompt into a 502; it is a rejection, so treat it as one.
        if self.is_build_request and self.role is None:
            self.is_build_request = False

        if not self.is_build_request and not self.rejection_message:
            self.rejection_message = (
                "Tell me whether you want a Survivor or a Killer build."
            )

        return self


# Named in English so the model cannot invent an axis, and fixed per role so
# two builds for the same role stay comparable.
SURVIVOR_AXES = ("Chase", "Information", "Objective", "Team Utility")
KILLER_AXES = ("Chase", "Map Pressure", "Slowdown", "Anti-Loop")

BuildAxisName = Literal[
    "Chase",
    "Information",
    "Objective",
    "Team Utility",
    "Map Pressure",
    "Slowdown",
    "Anti-Loop",
]


class PerkChoice(BaseModel):
    name: str = Field(description="Official perk name, in English")
    reason: str = Field(
        description="One sentence on why this perk is in this build, "
        "in the user's language"
    )


class AddonChoice(BaseModel):
    name: str = Field(description="Official addon name, in English")
    reason: str = Field(
        description="One short sentence on what this addon does for the kit, "
        "in the user's language"
    )


class ItemKit(BaseModel):
    kit_title: str = Field(
        description="Short kit purpose written in the user's language"
    )
    item_name: Optional[str] = Field(
        default=None, description="Item name (None if Killer role)"
    )
    item_reason: Optional[str] = Field(
        default=None,
        description="Why this item suits the build; null for Killer role",
    )
    addons: list[AddonChoice] = Field(
        min_length=2, max_length=2, description="Exactly 2 addons"
    )


class Synergy(BaseModel):
    entities: list[str] = Field(
        min_length=2,
        max_length=4,
        description=(
            "Names of perks, addons, items or the Killer power FROM THIS BUILD "
            "that combine. English names only, spelled exactly as chosen."
        ),
    )
    explanation: str = Field(
        description="What the combination achieves, in the user's language"
    )


class BuildAxis(BaseModel):
    axis: BuildAxisName
    score: int = Field(ge=1, le=5, description="How strong the build is on this axis")
    reason: str = Field(
        description="One short sentence justifying the score, in the user's language"
    )


class TargetAudienceBlock(BaseModel):
    title: str = Field(
        description="Short heading written in the user's language"
    )
    description: str = Field(description="Detailed explanation text")
    icon: LucideIcon


class TacticStep(BaseModel):
    title: str = Field(description="Action title")
    description: str = Field(description="Explanation step")


class GameTactics(BaseModel):
    early_game: list[TacticStep] = Field(description="Early game steps")
    mid_game: list[TacticStep] = Field(description="Mid game steps")
    late_game: list[TacticStep] = Field(description="Late game steps")


class ProConBlock(BaseModel):
    label: str = Field(description="Short label name")
    icon: LucideIcon
    tooltip_text: str = Field(description="Detailed explanation shown on hover")


class CounterKillerBlock(BaseModel):
    killer_name: str = Field(description="Killer name from DbD")
    # Three levels, not two: with only Medium and High every matchup in the
    # list reads as dangerous and the ranking says nothing. A build is allowed
    # to be merely inconvenienced by one of its five worst matchups.
    difficulty_level: Literal["Low Difficulty", "Medium Difficulty", "High Difficulty"]
    explanation: str = Field(
        description="Justification why this build suffers against this killer (for hover)"
    )


class CounterPerkBlock(BaseModel):
    """A perk the OTHER side brings that blunts this build.

    The mirror of counter_killers, and the only grounded answer to "what beats
    a Killer build": maps are not in the data, so a list of bad maps would be
    invention, while every perk here is checked against MongoDB like the rest.
    """

    perk_name: str = Field(
        description="Official perk name belonging to the opposing role, in English"
    )
    explanation: str = Field(
        description=(
            "How it blunts this build and what to do about it, "
            "in the user's language"
        )
    )


class DbDBuildSchema(BaseModel):
    build_title: str = Field(
        description="Main build slogan/title written in the user's language"
    )
    character_name: str = Field(
        description="Character matching the vibe or user query, e.g. 'Dwight Fairfield'"
    )
    role: Literal["Survivor", "Killer"]
    difficulty_rating: int = Field(
        ge=1, le=4, description="Build execution difficulty from 1 to 4"
    )

    perks: list[PerkChoice] = Field(
        min_length=4, max_length=4, description="Exactly 4 perks"
    )
    item_kits: list[ItemKit] = Field(
        min_length=2, max_length=2, description="Exactly 2 item/addon kits"
    )

    axes: list[BuildAxis] = Field(
        min_length=4,
        max_length=4,
        description="The four axes for this role, each scored once",
    )
    synergies: list[Synergy] = Field(
        min_length=2,
        max_length=3,
        description="How the chosen pieces work together",
    )

    target_audience: list[TargetAudienceBlock] = Field(min_length=2, max_length=3)
    tactics: GameTactics
    pros: list[ProConBlock] = Field(min_length=2, max_length=3)
    cons: list[ProConBlock] = Field(min_length=2, max_length=3)
    counter_killers: Optional[list[CounterKillerBlock]] = Field(
        default=None,
        min_length=5,
        max_length=5,
        description="Exactly 5 counter killers for Survivor; null for Killer",
    )
    counter_perks: list[CounterPerkBlock] = Field(
        min_length=3,
        max_length=3,
        description=(
            "Exactly 3 perks of the OPPOSING role that blunt this build. "
            "Killer perks for a Survivor build, Survivor perks for a Killer build."
        ),
    )

    @model_validator(mode="after")
    def validate_counter_killers(self):
        if self.role == "Survivor" and self.counter_killers is None:
            raise ValueError("Survivor builds require exactly 5 counter killers")

        if self.role == "Killer" and self.counter_killers is not None:
            raise ValueError("Killer builds must set counter_killers to null")

        return self
