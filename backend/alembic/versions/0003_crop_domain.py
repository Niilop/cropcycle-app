"""Replace the template examples with the crop rotation domain.

Drops the example `items` and `background_jobs` tables; their data is not carried over.
Downgrading recreates them empty.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_crop_domain"
down_revision = "0002_items"
branch_labels = None
depends_on = None

NEW_ENUMS = ("compatibility", "planstatus", "placementsource")


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def window() -> list[sa.Column]:
    return [
        sa.Column("start_month", sa.Date(), nullable=False),
        sa.Column("end_month", sa.Date(), nullable=False),
    ]


def upgrade() -> None:
    op.drop_index("ix_background_jobs_user_id", table_name="background_jobs")
    op.drop_table("background_jobs")
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_items_owner_id", table_name="items")
    op.drop_table("items")

    op.create_table(
        "crop_families",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("names", sa.JSON(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_crop_families_slug"),
    )
    op.create_table(
        "crops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("names", sa.JSON(), nullable=False),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("crop_families.id"), nullable=False),
        sa.Column("default_start_month", sa.Integer(), nullable=False),
        sa.Column("default_end_month", sa.Integer(), nullable=False),
        sa.Column("default_start_year_offset", sa.Integer(), nullable=False),
        sa.CheckConstraint("default_end_month BETWEEN 1 AND 12", name="ck_crops_end_month_range"),
        sa.CheckConstraint(
            "default_start_month BETWEEN 1 AND 12", name="ck_crops_start_month_range"
        ),
        sa.CheckConstraint(
            "default_start_year_offset IN (-1, 0)", name="ck_crops_start_year_offset"
        ),
        sa.UniqueConstraint("slug", name="uq_crops_slug"),
    )
    op.create_index("ix_crops_family_id", "crops", ["family_id"])
    op.create_table(
        "rotation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=True),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("crop_families.id"), nullable=True),
        sa.Column("preferred_gap_years", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "(crop_id IS NULL) <> (family_id IS NULL)", name="ck_rotation_rules_one_target"
        ),
        sa.CheckConstraint("preferred_gap_years >= 0", name="ck_rotation_rules_gap_non_negative"),
        sa.CheckConstraint("weight > 0", name="ck_rotation_rules_weight_positive"),
        sa.UniqueConstraint("crop_id", name="uq_rotation_rules_crop_id"),
        sa.UniqueConstraint("family_id", name="uq_rotation_rules_family_id"),
    )
    op.create_table(
        "companion_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crop_a_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("crop_b_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column(
            "compatibility",
            sa.Enum("positive", "neutral", "negative", name="compatibility"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint("crop_a_id < crop_b_id", name="ck_companion_rules_ordered_pair"),
        sa.CheckConstraint("weight > 0", name="ck_companion_rules_weight_positive"),
        sa.UniqueConstraint(
            "crop_a_id", "crop_b_id", name="uq_companion_rules_crop_a_id_crop_b_id"
        ),
    )
    op.create_index("ix_companion_rules_crop_b_id", "companion_rules", ["crop_b_id"])

    op.create_table(
        "gardens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_gardens_user_id", "gardens", ["user_id"])
    op.create_table(
        "beds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "garden_id",
            sa.Integer(),
            sa.ForeignKey("gardens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_beds_positive_size"),
    )
    op.create_index("ix_beds_garden_id", "beds", ["garden_id"])
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "garden_id",
            sa.Integer(),
            sa.ForeignKey("gardens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum("draft", "completed", name="planstatus"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("garden_id", "year", name="uq_plans_garden_id_year"),
    )
    op.create_table(
        "planned_crops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_planned_crops_quantity_positive"),
        sa.UniqueConstraint("plan_id", "crop_id", name="uq_planned_crops_plan_id_crop_id"),
    )
    op.create_index("ix_planned_crops_crop_id", "planned_crops", ["crop_id"])
    op.create_table(
        "plan_placements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "bed_id", sa.Integer(), sa.ForeignKey("beds.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        *window(),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("source", sa.Enum("manual", "suggested", name="placementsource"), nullable=False),
        *timestamps(),
        sa.CheckConstraint("start_month <= end_month", name="ck_plan_placements_window_order"),
    )
    for column in ("plan_id", "bed_id", "crop_id"):
        op.create_index(f"ix_plan_placements_{column}", "plan_placements", [column])
    op.create_table(
        "plantings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bed_id", sa.Integer(), sa.ForeignKey("beds.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        *window(),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column(
            "plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
        ),
        *timestamps(),
        sa.CheckConstraint("start_month <= end_month", name="ck_plantings_window_order"),
        sa.CheckConstraint("coverage > 0 AND coverage <= 1", name="ck_plantings_coverage_range"),
    )
    for column in ("bed_id", "crop_id", "year", "plan_id"):
        op.create_index(f"ix_plantings_{column}", "plantings", [column])


def downgrade() -> None:
    for table in (
        "plantings",
        "plan_placements",
        "planned_crops",
        "plans",
        "beds",
        "gardens",
        "companion_rules",
        "rotation_rules",
        "crops",
        "crop_families",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for name in NEW_ENUMS:
        sa.Enum(name=name).drop(bind, checkfirst=True)

    # The template examples come back empty; their former rows were not retained.
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_items_owner_id", "items", ["owner_id"])
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="jobstatus"),
            nullable=False,
        ),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_background_jobs_user_id", "background_jobs", ["user_id"])
