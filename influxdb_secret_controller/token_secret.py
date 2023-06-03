import base64
import logging
import os

import kubernetes

from . import config


class InfluxTokenSecret:
    def __init__(
        self,
        name: str,
        namespace: str,
        token: str,
        api: kubernetes.client.CoreV1Api,
        instance_name: str,
    ):
        self.name = name
        self.namespace = namespace
        self.token = token
        self.api = api
        self.instance_name = instance_name

    def create(self):
        meta = kubernetes.client.V1ObjectMeta(
            labels={
                "managed_by_isc": "true",
                "isc_name": instance_name,
            }
        )
        secret = kubernetes.client.V1Secret(
            metadata=meta, string_data={"token": self.token}
        )
        try:
            res = self.api.create_namespaced_secret(
                self.namespace,
                secret,
                pretty=_is_debug(),
            )
            logging.debug(res)
        except kubernetes.client.ApiException as e:
            logging.exeception(
                "Exception when calling CoreV1Api->create_namespaced_secret: %s\n", e
            )

    def delete(self):
        try:
            res = self.api.delete_namespaced_secret(
                self.name,
                self.namespace,
                pretty=_is_debug(),
            )
            logging.debug(res)
        except kubernetes.client.ApiException as e:
            logging.exeception(
                "Exception when calling CoreV1Api->delete_namespaced_secret: %s\n", e
            )


class KubeClient:
    def __init__(self, config: config.Config):
        self.client = self._get_k8s_config()
        self.debug = config.debug
        self.deployment_name = config.deployment_name

    def get_current_secrets(
        self, limit: int = 100, cont: bool = False
    ) -> list[InfluxTokenSecret]:
        try:
            res = self.client.list_secret_for_all_namespaces(
                pretty=self.config.debug,
                label_selector="managed_by_isc=true",
                limit=limit,
                # Maybe we'll need this eventually?
                # timeout_seconds=timeout_seconds,
            )

        except kubernetes.client.ApiException as e:
            logging.exception(
                "Exception when calling CoreV1Api->list_namespaced_secret: %s\n", e
            )
            return []
        secrets: list[InfluxTokenSecret] = []
        for secret in res.list:
            deployment_name = secret["metadata"]["labels"].get("isc_name")
            if deployment_name != self.deployment_name:
                logging.warning(
                    f"found a secret that doesn't match our deployment name! {deployment_name} vs {self.deployment_name}"
                )
            token = base64.b64decode(secret["data"].get("token", "")).decode()
            secrets.append(
                InfluxTokenSecret(
                    name=secret["metadata"]["name"],
                    namespace=secret["metadata"]["namespace"],
                    token=token,
                    api=self.client,
                    instance_name=self.deployment_name,
                )
            )
        if res.metadata._continue:
            return secrets + get_current_secrets(api, limit, cont=True)
        return secrets

    def _get_k8s_config(self) -> kubernetes.client.CoreV1Api:
        kubernetes.config.load_incluster_config()
        return kubernetes.client.CoreV1Api()
