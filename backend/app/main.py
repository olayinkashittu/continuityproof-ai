
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.app.database import DATABASE_PATH, get_connection, initialize_database

app = FastAPI(
    title="ContinuityProof AI",
    description="An AI-powered IT infrastructure recovery verification platform.",
    version="0.2.0"
)

initialize_database()


class AssetCreate(BaseModel):
    asset_name: str = Field(min_length=1, max_length=100)
    asset_type: str = Field(min_length=1, max_length=50)
    hostname: str | None = None
    operating_system: str | None = None
    environment: str = Field(default="unknown", min_length=1)

    @field_validator("asset_name", "asset_type", "environment")
    @classmethod
    def reject_blank_values(cls, value):
        if not value.strip():
            raise ValueError("This field cannot contain only spaces.")
        return value.strip()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value):
        allowed_environments = {
            "production",
            "development",
            "testing",
            "staging",
            "unknown"
        }

        if value.lower() not in allowed_environments:
            raise ValueError("Invalid environment value.")

        return value.lower()


@app.get("/")
def home():
    return {
        "product": "ContinuityProof AI",
        "message": "Welcome to ContinuityProof AI",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ContinuityProof AI backend"
    }


@app.post("/assets", status_code=201)
def register_asset(asset: AssetCreate):
    connection = get_connection()

    try:
        # Prevent duplicate hostnames
        if asset.hostname and asset.hostname.strip():
            existing_asset = connection.execute(
                """
                SELECT id FROM assets
                WHERE LOWER(TRIM(hostname)) = LOWER(TRIM(?))
                """,
                (asset.hostname,)
            ).fetchone()

            if existing_asset:
                raise HTTPException(
                    status_code=409,
                    detail=f"An asset with hostname '{asset.hostname}' already exists."
                )

        cursor = connection.execute(
            """
            INSERT INTO assets
            (asset_name, asset_type, hostname, operating_system, environment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                asset.asset_name,
                asset.asset_type,
                asset.hostname,
                asset.operating_system,
                asset.environment
            )
        )

        connection.commit()

        new_asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return dict(new_asset)

    finally:
        connection.close()


@app.get("/assets/{asset_id}")
def get_asset(asset_id: int):
    connection = get_connection()

    try:
        asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,)
        ).fetchone()

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail="Asset not found."
            )

        return dict(asset)

    finally:
        connection.close()

@app.put("/assets/{asset_id}")
def update_asset(asset_id: int, asset: AssetCreate):
    connection = get_connection()

    try:
        existing_asset = connection.execute(
            "SELECT id FROM assets WHERE id = ?",
            (asset_id,)
        ).fetchone()

        if existing_asset is None:
            raise HTTPException(
                status_code=404,
                detail="Asset not found."
            )

        # Prevent another asset from using the same hostname
        if asset.hostname and asset.hostname.strip():
            duplicate = connection.execute(
                """
                SELECT id FROM assets
                WHERE LOWER(TRIM(hostname)) = LOWER(TRIM(?))
                AND id != ?
                """,
                (asset.hostname, asset_id)
            ).fetchone()

            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail="Another asset already uses this hostname."
                )

        connection.execute(
            """
            UPDATE assets
            SET asset_name = ?,
                asset_type = ?,
                hostname = ?,
                operating_system = ?,
                environment = ?
            WHERE id = ?
            """,
            (
                asset.asset_name,
                asset.asset_type,
                asset.hostname,
                asset.operating_system,
                asset.environment,
                asset_id
            )
        )

        connection.commit()

        updated_asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,)
        ).fetchone()

        return dict(updated_asset)

    finally:
        connection.close()

@app.get("/assets")
def list_assets():
    connection = get_connection()

    try:
        assets = connection.execute(
            "SELECT * FROM assets ORDER BY id"
        ).fetchall()

        return [dict(asset) for asset in assets]

    finally:
        connection.close()


@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int):
    connection = get_connection()

    try:
        existing_asset = connection.execute(
            "SELECT id FROM assets WHERE id = ?",
            (asset_id,)
        ).fetchone()

        if existing_asset is None:
            raise HTTPException(
                status_code=404,
                detail="Asset not found."
            )

        connection.execute(
            "DELETE FROM assets WHERE id = ?",
            (asset_id,)
        )

        connection.commit()

        return {
            "message": "Asset deleted successfully.",
            "asset_id": asset_id
        }

    finally:
        connection.close()
