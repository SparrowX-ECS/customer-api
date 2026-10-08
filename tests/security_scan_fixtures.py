"""Temporary intentionally vulnerable fixtures for DevSecOps scanner testing.

This file is not imported by the application and must be removed after the
source-security workflow has been validated.
"""

from fastapi import Request


# Deliberately fake test-only credentials for secret-scanning validation.
TEST_AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
TEST_AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def intentionally_vulnerable_query(request: Request, connection):
    """Deliberately unsafe SQL construction for SAST validation only."""
    customer_id = request.query_params["customer_id"]
    query = "SELECT * FROM customers WHERE id = " + customer_id
    return connection.execute(query)
