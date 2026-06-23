"""initial schema

Esquema inicial de apsis: extension PostGIS, dominio tracking (satellites,
ground_stations, pass_predictions con geometrias WGS84) y la infra
Postgres-nativa (scheduled_jobs, outbox_events con indices parciales). Siembra
el job recurrente tle_refresh.

Revision ID: 3bc965b4d0d6
Revises:
Create Date: 2026-06-23 22:23:39.314274

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3bc965b4d0d6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostGIS debe existir antes de crear cualquier columna Geometry. El rol de
    # BD necesita privilegio para CREATE EXTENSION (superuser o extension
    # preinstalada).
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_geospatial_table(
        "ground_stations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326, dimension=2, spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry", nullable=False), nullable=False),
        sa.Column("altitude_m", sa.Float(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ground_stations")),
        sa.UniqueConstraint("name", name=op.f("uq_ground_stations_name")),
    )
    op.create_geospatial_index("idx_ground_stations_location", "ground_stations", ["location"], unique=False, postgresql_using="gist", postgresql_ops={})

    op.create_table(
        "satellites",
        sa.Column("norad_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tle_line1", sa.Text(), nullable=False),
        sa.Column("tle_line2", sa.Text(), nullable=False),
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satellites")),
        sa.UniqueConstraint("norad_id", name=op.f("uq_satellites_norad_id")),
    )
    op.create_index("ix_satellites_name", "satellites", ["name"], unique=False)

    op.create_geospatial_table(
        "pass_predictions",
        sa.Column("satellite_id", sa.UUID(), nullable=False),
        sa.Column("ground_station_id", sa.UUID(), nullable=False),
        sa.Column("aos_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("los_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("peak_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("peak_elevation_deg", sa.Float(), nullable=False),
        sa.Column("track", Geometry(geometry_type="LINESTRING", srid=4326, dimension=2, spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry", nullable=False), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ground_station_id"], ["ground_stations.id"], name=op.f("fk_pass_predictions_ground_station_id_ground_stations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["satellite_id"], ["satellites.id"], name=op.f("fk_pass_predictions_satellite_id_satellites"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pass_predictions")),
        sa.UniqueConstraint("satellite_id", "ground_station_id", "aos_at", name="uq_pass_predictions_sat_station_aos"),
    )
    op.create_geospatial_index("idx_pass_predictions_track", "pass_predictions", ["track"], unique=False, postgresql_using="gist", postgresql_ops={})
    op.create_index("ix_pass_predictions_ground_station_id_aos_at", "pass_predictions", ["ground_station_id", "aos_at"], unique=False)

    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("run_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_jobs")),
        sa.UniqueConstraint("job_name", name=op.f("uq_scheduled_jobs_job_name")),
    )
    op.create_index("scheduled_jobs_pending_idx", "scheduled_jobs", ["next_run_at"], unique=False, postgresql_where=sa.text("status = 'PENDING'"))

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=True),
        sa.Column("correlation_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="8", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handler_state", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index("outbox_events_aggregate_idx", "outbox_events", ["aggregate_id"], unique=False, postgresql_where=sa.text("aggregate_id IS NOT NULL"))
    op.create_index("outbox_events_correlation_idx", "outbox_events", ["correlation_id"], unique=False, postgresql_where=sa.text("correlation_id IS NOT NULL"))
    op.create_index("outbox_events_pending_idx", "outbox_events", ["scheduled_at"], unique=False, postgresql_where=sa.text("status = 'PENDING'"))

    # Siembra el cron tle_refresh (CelesTrak recalcula los GP cada 2h).
    op.execute(
        "INSERT INTO scheduled_jobs (job_name, description, interval_seconds, next_run_at, status) "
        "VALUES ('tle_refresh', 'Refresca los TLEs del grupo CelesTrak y upserta los satelites.', "
        "7200, now(), 'PENDING') ON CONFLICT (job_name) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("outbox_events_pending_idx", table_name="outbox_events", postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_index("outbox_events_correlation_idx", table_name="outbox_events", postgresql_where=sa.text("correlation_id IS NOT NULL"))
    op.drop_index("outbox_events_aggregate_idx", table_name="outbox_events", postgresql_where=sa.text("aggregate_id IS NOT NULL"))
    op.drop_table("outbox_events")
    op.drop_index("scheduled_jobs_pending_idx", table_name="scheduled_jobs", postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_table("scheduled_jobs")
    op.drop_index("ix_pass_predictions_ground_station_id_aos_at", table_name="pass_predictions")
    op.drop_geospatial_index("idx_pass_predictions_track", table_name="pass_predictions", postgresql_using="gist", column_name="track")
    op.drop_geospatial_table("pass_predictions")
    op.drop_index("ix_satellites_name", table_name="satellites")
    op.drop_table("satellites")
    op.drop_geospatial_index("idx_ground_stations_location", table_name="ground_stations", postgresql_using="gist", column_name="location")
    op.drop_geospatial_table("ground_stations")
