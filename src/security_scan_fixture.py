"""Temporary vulnerable fixture for source-scanner validation only.

This module is intentionally not imported by the application and must be
removed immediately after validating the DevSecOps pipeline.
"""

import sqlite3

from fastapi import Request


# Deliberately fake credential-shaped values for Trivy secret scanning.
TEST_GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
TEST_AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"


def intentionally_vulnerable_query(
    request: Request, connection: sqlite3.Connection
):
    """Deliberately unsafe SQL construction for Semgrep validation only."""
    customer_id = request.query_params["customer_id"]
    query = "SELECT * FROM customers WHERE id = " + customer_id
    cursor = connection.cursor()
    return cursor.execute(query)
