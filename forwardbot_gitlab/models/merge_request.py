import logging
from typing import Any, Dict, Sequence, Tuple

from odoo import api, fields, models
from requests import Request, Session

from ..api import get_api_data

_logger = logging.getLogger(__name__)


class MergeRequest(models.Model):
    _name = "forwardbot_gitlab.merge.request"
    _description = "Gitlab Merge Request (fwbot)"

    name = fields.Char(help="Merge Request Title", required=True)
    global_id = fields.Integer(
        help="ID for this MR on the remote server. Unique across all projects"
    )
    project_iid = fields.Integer(help="Internal ID. Unique inside the target project.")
    source_branch = fields.Char(required=True)
    source_project_id = fields.Integer(required=True)
    target_branch = fields.Char(required=True)
    target_project_id = fields.Integer(required=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("opened", "Opened"),
            ("closed", "Closed"),
            ("locked", "Locked"),
            ("merged", "Merged"),
        ],
        default="pending",
        required=True,
    )
    forward_port_id = fields.Many2one("forwardbot_gitlab.merge.request")
    processed = fields.Boolean(default=False)

    _sql_constraints = [
        (
            "unique_global_id",
            "UNIQUE (global_id)",
            "Two MRs can't have the same ID",
        ),
    ]

    required_merge_request_fields = [
        "id",
        "iid",
        "title",
        "target_branch",
        "source_branch",
        "state",
    ]

    def gen_api_merge_request(self, base_url: str, description: str = "") -> Request:
        self.ensure_one()
        req = Request(
            "POST",
            f"{base_url}/api/v4/projects/{self.target_project_id}/merge_requests",
            json={
                "id": self.source_project_id,
                "source_branch": self.source_branch,
                "target_branch": self.target_branch,
                "title": self.name,
                "description": description,
            },
            headers={"Content-Type": "application/json"},
        )

        return req

    def create_forward_port(self) -> "MergeRequest":
        self.ensure_one()
        if self.forward_port_id:
            return self.forward_port_id

        try:
            forward_branch = str(float(self.target_branch) + 1)
        except ValueError:
            return self.env["forwardbot_gitlab.merge.request"]

        self.forward_port_id = self.create(
            {
                "name": f"[FW]{self.name}",
                "source_project_id": self.source_project_id,
                "source_branch": self.source_branch,
                "target_project_id": self.target_project_id,
                "target_branch": forward_branch,
            }
        )
        return self.forward_port_id

    def update_from_object_attributes(self, object_attributes: Dict[str, Any]):
        self.ensure_one()
        self.validate_object_attributes(object_attributes)
        self.write(
            {
                "name": object_attributes["title"],
                "state": object_attributes["state"],
                "target_branch": object_attributes["target_branch"],
            }
        )

    @api.model
    def validate_object_attributes(self, object_attributes: Dict):
        for field in self.required_merge_request_fields:
            if not object_attributes.get(field):
                raise ValueError(f"missing field object_attributes.{field}")

    @api.model
    def obtain_from_event(self, data: Dict) -> Tuple["MergeRequest", bool]:
        """Obtain (search and create if not found) a record based on the data
        provided by a Merge Request event as described by Gitlab on:
        https://docs.gitlab.com/ee/user/project/integrations/webhook_events.html#merge-request-events
        """
        data_object = data.get("object_attributes", {})
        self.validate_object_attributes(data_object)

        merge_request = self.search([("global_id", "=", data_object["id"])])
        if merge_request:
            return merge_request, False

        return (
            self.env["forwardbot_gitlab.merge.request"].create(
                {
                    "name": data_object["title"],
                    "source_branch": data_object["source_branch"],
                    "source_project_id": data_object["source_project_id"],
                    "target_branch": data_object["target_branch"],
                    "target_project_id": data_object["target_project_id"],
                    "global_id": data_object["id"],
                    "project_iid": data_object["iid"],
                    "state": data_object["state"],
                }
            ),
            True,
        )

    @api.model
    def process_pending_for_forward_ports(
        self,
        auto_commit=False,
        limit=50,
        timeout=10,
        states: Sequence[str] = None,
    ):
        url, token = get_api_data(self.env)
        if not url or not token:
            return

        if states is None:
            states = ["merged"]

        pending_for_fw: Sequence[MergeRequest] = self.search(
            [
                ("forward_port_id", "=", False),
                ("processed", "=", False),
                ("state", "in", states),
            ],
            limit=limit,
            order="id",
        )
        _logger.info(
            "Will process %d MRs waiting for a forward port", len(pending_for_fw)
        )
        if not pending_for_fw:
            return

        session = Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        for merge_request in pending_for_fw:
            merge_request.create_forward_port()
            request = session.prepare_request(
                merge_request.forward_port_id.gen_api_merge_request(
                    url,
                    f"This is an automatic forward port for !{merge_request.project_iid}",
                )
            )
            response = session.send(request, timeout=timeout)
            if response.status_code not in [200, 201]:
                _logger.warning(
                    "Received status code %d when creating forward port for %s",
                    response.status_code,
                    merge_request,
                )
                continue

            try:
                data = response.json()
                merge_request.forward_port_id.write(
                    {
                        "id": data["id"],
                        "iid": data["iid"],
                        "state": data["state"],
                        "processed": True,
                    }
                )
                merge_request.processed = True
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception as ex:
                _logger.warning(
                    "Exception %s occurred while processing %s", ex, merge_request
                )
                continue

            _logger.info(
                "Forward port %s successfully pushed to Gitlab",
                merge_request.forward_port_id,
            )
