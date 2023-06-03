import logging

from . import config, influxdb, token_secret


def set_logging_config():
    logging.basicConfig(format="[%(asctime)s] [%(level)s] - %(message)s", level="INFO")


def diff_secrets(secrets, config) -> tuple[list, list]:
    needed = config.requested_secrets.copy()
    extras = []
    for secret in secrets:
        for requested in needed:
            matches_name = requested.name = secret.name
            matches_namespace = requested.namespace = secret.namespace
            if matches_name and matches_namespace:
                logging.info(
                    f"found a match for {requested.name} in {requested.namespace}. Skipping"
                )
                needed.remove(requested)
                break
        else:
            logging.info(
                f"found stale secret with no match '{secret.name}' in {secret.namespace}"
            )
            extra.append(secret)
    return needed, extras


def get_current_influxdb_state(client):
    logging.info("finding existing tokens...")
    tokens: list[influxdb.Token] = influxdb.get_tokens(client)
    logging.info("finding orgs...")
    orgs: list[influxdb.Org] = influxdb.get_orgs(client)
    buckets: dict[str, list[influxdb.Bucket]] = {}
    logging.info("finding buckets in orgs")
    for org in orgs:
        buckets[org.name] = influxdb.get_buckets(client, org)
    return orgs, buckets, tokens


def remote_extra_secrets(extras):
    for secret in extras:
        logging.info(f"deleting extra secret {secret.name}")
        secret.delete()


def create_new_secrets(k8_client, needed_secrets):
    influx_client = influxdb.Client(config)
    orgs, buckets, tokens = get_current_influxdb_state(influx_client)
    for secret in needed:
        token_name = f"{secret.name}-{secret.namespace}"
        for token in tokens:
            name_matches = token.name == token_name
            org_matches = token.org.name == secret.org
            bucket_matches = token.bucket and token.bucket.name == secret.bucket
            if name_matches and org_matches and bucket_matches:
                logging.warning(
                    f"token already exists for {token_name}? Using pre-existing one"
                )
                break
        else:
            logging.info(f"creating token for {secret.name} in {secret.namespace}")
            for org in orgs:
                if org.name == secret.org:
                    logging.info(f"found org {org.name}")
                    break
            else:
                logging.info(f"needed to create org {secret.org}")
                org = influxdb.Org(id=None, name=secret.org, client=influx_client)
                org.create()
                orgs.append(org)
            bucket = None
            if secret.bucket:
                if buckets.get(org.name) is None:
                    buckets[org.name] = []
                for bucket in buckets[org.name]:
                    if bucket.name == secret.bucket:
                        logging.info(f"found bucket {bucket.name}")
                        break
                else:
                    logging.info(f"needed to create bucket {secret.bucket}")
                    bucket = influxdb.Bucket(
                        id=None, name=secret.bucket, org=org, client=influx_client
                    )
                    bucket.create()
                    buckets[org.name].append(bucket)
            token = influxdb.Token(
                id=None,
                name=token_name,
                org=org,
                bucket=bucket,
                client=influx_client,
                permissions=secret.permissions,
            )
        secret = k8s_client.new_secret(secret, token)


def main():
    set_logging_config()
    cfg = config.Config()
    k8s_client = token_secret.KubeClient(cfg)
    logging.info("finding owned secrets")
    secrets = k8s_client.get_current_secrets()
    needed, extras = diff_secrets(secrets, cfg)

    if extras:
        logging.info(f"cleaning up {len(extras)} old secrets")
        remove_extra_secrets(extras)

    if needed:
        logging.info(f"creating {len(needed)} new secrets")
        create_new_secrets(k8s_client, needed)
    else:
        logging.info("didn't need to create any new secrets.")
