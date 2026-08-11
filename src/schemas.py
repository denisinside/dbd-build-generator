from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# Allowed Lucide registry icons
LucideIcon = Literal[
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


class BuildRequestAnalysis(BaseModel):
    is_build_request: bool = Field(
        description="True only when the user clearly asks for a DbD build"
    )
    role: Optional[Literal["Survivor", "Killer"]] = Field(
        default=None,
        description="Requested DbD role; null when missing or unclear",
    )
    output_language: str = Field(
        description="English name of the language to use for generated prose"
    )
    rejection_message: Optional[str] = Field(
        default=None,
        description="Short user-facing error when the request is rejected",
    )

    @model_validator(mode="after")
    def validate_request_analysis(self):
        if self.is_build_request and self.role is None:
            raise ValueError("Accepted build requests must have a role")

        if not self.is_build_request and not self.rejection_message:
            raise ValueError("Rejected requests must have a rejection message")

        return self


class ItemKit(BaseModel):
    kit_title: str = Field(
        description="Short kit purpose written in the user's language"
    )
    item_name: Optional[str] = Field(
        default=None, description="Item name (None if Killer role)"
    )
    addons: list[str] = Field(
        min_length=2, max_length=2, description="Exactly 2 addon names"
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
    difficulty_level: Literal["Medium Difficulty", "High Difficulty"]
    explanation: str = Field(
        description="Justification why this build suffers against this killer (for hover)"
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
    build_score: int = Field(ge=1, le=10, description="Overall rating from 1 to 10")

    perks: list[str] = Field(
        min_length=4, max_length=4, description="Exactly 4 perk names"
    )
    item_kits: list[ItemKit] = Field(
        min_length=2, max_length=2, description="Exactly 2 item/addon kits"
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

    @model_validator(mode="after")
    def validate_counter_killers(self):
        if self.role == "Survivor" and self.counter_killers is None:
            raise ValueError("Survivor builds require exactly 5 counter killers")

        if self.role == "Killer" and self.counter_killers is not None:
            raise ValueError("Killer builds must set counter_killers to null")

        return self
