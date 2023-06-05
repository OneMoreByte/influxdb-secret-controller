import logging
from typing import Any, Optional

import requests

from . import config


class Client:
    def __init__(self, cfg: config.Config):
        self.uri = cfg.influxdb_uri
        self.token = cfg.influxdb_token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    def get(self, path: str) -> Any:
        res: requests.Response = requests.get(self.uri + path, headers=self.headers)
        if res.status_code == 401:
            logging.error("user is unauthorized for getting!")
            return None
        res.raise_for_status
        return res.json()

    def post(self, path: str, payload: Optional[dict[Any, Any]] = None) -> Any:
        res: requests.Response = requests.post(
            self.uri + path, headers=self.headers, json=payload
        )
        if res.status_code == 401:
            logging.error("user is unauthorized for creating!")
            return None
        res.raise_for_status
        return res.json()

    def delete(self, path: str):
        res: requests.Response = requests.delete(
            self.uri + path,
            headers=self.headers,
        )
        if res.status_code == 401:
            logging.error("user is unauthorized for deleting!")
            return None
        res.raise_for_status
        return res.json()


class Org:
    def __init__(self, id: Optional[str], name: str, client: Client):
        self.id = id
        self.name = name
        self.client = client

    def create(self):
        logging.info(f"creating org {self.name}")
        res = self.client.post("/api/v2/orgs", payload={"name": self.name})
        self.id = res.get("id")
        logging.info("successfully created org")


class Bucket:
    def __init__(self, id: Optional[str], name: str, org: Org, client: Client):
        self.id = id
        self.name = name
        self.org = org
        self.client = client

    def create(self):
        logging.info(f"creating bucket {self.name} in {self.org.name}")
        payload = {
            "name": self.name,
            "orgID": self.org.id,
        }
        res = self.client.post("/api/v2/orgs", payload=payload)
        self.id = res.get("id")
        logging.info("successfully created bucket")


class Token:
    def __init__(
        self,
        name: str,
        org: Org,
        client: Client,
        permissions: str,
        id: Optional[str] = None,
        bucket: Optional[Bucket] = None,
    ):
        self.name = name
        self.id = id
        self.org = org
        self.client = client
        self.bucket = bucket
        self.permissions = permissions

    def create(self):
        logging.info(
            f"creating token {self.name} in {self.org.name} with {self.permissions}"
        )
        permissions = []
        resource_types = [
            "buckets",
            "dashboards",
            "variables",
            "labels",
            "views",
            "documents",
            "checks," "dbrp",
            "notebooks",
            "annotations",
            "remotes",
            "replications",
        ]
        for resource_type in resource_types:
            permissions.append(
                {
                    "action": self.permissions,
                    "resource": {
                        "orgID": self.org.id,
                        "type": resource_type,
                    },
                }
            )
        payload = {
            "status": "active",
            "description": self.name,
            "orgID": self.org.id,
            "permissions": permissions,
        }
        raw_token = self.client.post("/api/v2/authorizations", payload)
        self.id = raw_token.get("id")
        self.token = raw_token.get("token")
        if self.id and self.token:
            logging.info("successfully created token")
        else:
            logging.error("failed to create token!")

    def delete(self):
        logging.info(f"deleting token {self.name} in {self.org.name}")
        self.client.delete("/api/v2/authorizations")
        logging.info("successfully deleted token")


def get_orgs(client: Client) -> list[Org]:
    raw_orgs = client.get("/api/v2/orgs")
    orgs: list[Org] = []
    if raw_orgs:
        for org_json in raw_orgs.get("orgs", []):
            orgs.append(Org(org_json["id"], org_json["name"], client))
    return orgs


def get_buckets(client: Client, org: Org) -> list[Bucket]:
    raw_buckets = client.get(f"/api/v2/buckets?orgID={org.id}")
    buckets: list[Bucket] = []
    if raw_buckets:
        for bucket_json in raw_buckets.get("buckets"):
            buckets.append(Bucket(bucket_json["id"], bucket_json["name"], org, client))
    return buckets


def get_tokens(
    client: Client,
) -> list[Token]:
    raw_tokens = client.get("/api/v2/authorizations")
    tokens: list[Token] = []
    if raw_tokens:
        for token_json in raw_tokens.get("authorizations"):
            org = Org(token_json["orgID"], token_json["org"], client)
            permissions = token_json["permissions"]
            bucket = None
            if permissions[0].get("name"):
                bucket = Bucket(
                    permissions[0]["id"], permissions[0]["name"], org, client
                )
            tokens.append(
                Token(
                    token_json["description"],
                    org,
                    client,
                    permissions[0]["action"],
                    token_json["id"],
                    bucket,
                )
            )
    return tokens
