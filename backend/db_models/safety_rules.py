import uuid

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class SafetyRule(SQLModel, table=True):
	__tablename__ = "safety_rules"
	__table_args__ = (
		sa.UniqueConstraint("device_id", "action_type", name="safety_rules_device_action_unique"),
		sa.CheckConstraint("action_type IN ('run_for_duration')"),
		sa.CheckConstraint("max_duration_seconds > 0"),
		sa.CheckConstraint("cooldown_seconds >= 0"),
	)

	rule_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	device_id: uuid.UUID = Field(foreign_key="devices.device_id")
	action_type: str = Field(
		default="run_for_duration", sa_column=sa.Column(sa.Text, nullable=False, server_default="run_for_duration")
	)
	max_duration_seconds: int
	cooldown_seconds: int = Field(default=0, sa_column=sa.Column(sa.Integer, nullable=False, server_default="0"))
	enabled: bool = Field(default=True, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.true()))
