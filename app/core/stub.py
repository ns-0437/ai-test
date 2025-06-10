import json
import logging
from typing import Any, Dict, List, Literal, Tuple

import requests

from openfabric_pysdk.helper import has_resource_fields, json_schema_to_marshmallow, resolve_resources

# Type aliases for clarity
Manifests = Dict[str, dict]
Schemas = Dict[str, Tuple[dict, dict]]

OPENFABRIC_NODE = "https://node2.openfabric.network"

class Stub:
    """
    Stub acts as a lightweight client interface that initializes remote connections
    to multiple Openfabric applications, fetching their manifests, schemas, and enabling
    execution of calls to these apps.
    """

    def __init__(self, app_ids: List[str]):
        self._schema: Schemas = {}
        self._manifest: Manifests = {}
        self.app_ids = app_ids

        for app_id in app_ids:
            try:
                # Fetch manifest
                manifest_url = f"{OPENFABRIC_NODE}/api/app/{app_id}/manifest"
                manifest = requests.get(manifest_url, timeout=5).json()
                logging.info(f"[{app_id}] Manifest loaded: {manifest}")
                self._manifest[app_id] = manifest

                # Fetch input schema
                input_schema_url = f"{OPENFABRIC_NODE}/api/app/{app_id}/schema?type=input"
                input_schema = requests.get(input_schema_url, timeout=5).json()
                logging.info(f"[{app_id}] Input schema loaded: {input_schema}")

                # Fetch output schema
                output_schema_url = f"{OPENFABRIC_NODE}/api/app/{app_id}/schema?type=output"
                output_schema = requests.get(output_schema_url, timeout=5).json()
                logging.info(f"[{app_id}] Output schema loaded: {output_schema}")

                self._schema[app_id] = (input_schema, output_schema)
            except Exception as e:
                logging.error(f"[{app_id}] Initialization failed: {e}")

    def call(self, app_id: str, data: Any, uid: str = 'super-user') -> dict:
        """
        Sends a request to the specified app via the Openfabric node REST API.
        """
        if app_id not in self.app_ids:
            raise Exception(f"App ID not initialized: {app_id}")

        try:
            url = f"{OPENFABRIC_NODE}/api/app/{app_id}/run"
            payload = data.copy() if isinstance(data, dict) else dict(data)
            payload['uid'] = uid
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Optionally handle output schema and resources
            schema = self.schema(app_id, 'output')
            marshmallow = json_schema_to_marshmallow(schema)
            handle_resources = has_resource_fields(marshmallow())

            if handle_resources:
                # This assumes resource URLs are also served from the node
                result = resolve_resources(
                    f"{OPENFABRIC_NODE}/api/app/{app_id}/resource?reid={{reid}}",
                    result,
                    marshmallow()
                )

            return result
        except Exception as e:
            logging.error(f"[{app_id}] Execution failed: {e}")
            raise

    def manifest(self, app_id: str) -> dict:
        return self._manifest.get(app_id, {})

    def schema(self, app_id: str, type: Literal['input', 'output']) -> dict:
        _input, _output = self._schema.get(app_id, (None, None))
        if type == 'input':
            if _input is None:
                raise ValueError(f"Input schema not found for app ID: {app_id}")
            return _input
        elif type == 'output':
            if _output is None:
                raise ValueError(f"Output schema not found for app ID: {app_id}")
            return _output
        else:
            raise ValueError("Type must be either 'input' or 'output'")