import logging
import re
from typing import Any, Dict, Sequence, Tuple

from odoo import api, fields, models

from ..api import ForwardbotClient, get_api_data
from .project import Project

_logger = logging.getLogger(__name__)


class MergeRequest(models.Model):
    _name = "forwardbot_gitlab.merge.request"
    _description = "Gitlab Merge Request (fwbot)"
    _fwbranch_regex = re.compile(r"-fw\d+.*$")

    name = fields.Char(help="Merge Request Title", required=True)
    global_id = fields.Integer(help="ID for this MR on the remote server. Unique across all projects")
    project_iid = fields.Integer(help="Internal ID. Unique inside the target project.")
    source_branch = fields.Char(required=True)
    source_project_id = fields.Integer(required=True)
    target_branch = fields.Char(required=True)
    target_project_id: Project = fields.Many2one("forwardbot_gitlab.project", required=True)
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
    forward_port_id: "MergeRequest" = fields.Many2one("forwardbot_gitlab.merge.request")
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
        "target_project_id",
        "source_project_id",
        "state",
    ]

    @api.multi
    def create_forward_port(self) -> "MergeRequest":
        self.ensure_one()
        if self.forward_port_id:
            return self.forward_port_id

        forward_branch = self.target_project_id.get_next_branch(self.target_branch)
        if not forward_branch:
            return self

        original_source = self._fwbranch_regex.sub("", self.source_branch)
        source_branch = f"{forward_branch}-{original_source}-fw{self.id}"
        name = self.name
        if not self.name.startswith("[FW]"):
            name = f"[FW]{name}"

        self.forward_port_id = self.create(
            {
                "name": name,
                "source_project_id": self.source_project_id,
                "source_branch": source_branch,
                "target_project_id": self.target_project_id.id,
                "target_branch": forward_branch,
            }
        )

        return self.forward_port_id

    @api.multi
    def update_from_object_attributes(self, object_attributes: Dict[str, Any]):
        self.ensure_one()
        self.validate_object_attributes(object_attributes)
        self.write(
            {
                "name": object_attributes["title"],
                "state": object_attributes["state"],
                "target_branch": object_attributes["target_branch"],
                "processed": False,
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

        target_project_id = data_object["target_project_id"]
        target_project = self.env["forwardbot_gitlab.project"].search([("remote_id", "=", target_project_id)], limit=1)
        if not target_project:
            target_project = self.env["forwardbot_gitlab.project"].create({"remote_id": target_project_id})

        return (
            self.env["forwardbot_gitlab.merge.request"].create(
                {
                    "name": data_object["title"],
                    "source_branch": data_object["source_branch"],
                    "source_project_id": data_object["source_project_id"],
                    "target_branch": data_object["target_branch"],
                    "target_project_id": target_project.id,
                    "global_id": data_object["id"],
                    "project_iid": data_object["iid"],
                    "state": data_object["state"],
                }
            ),
            True,
        )

    @api.model
    def prune_merge_requests(self, auto_commit=False, limit=50, timeout=10):
        url, token = get_api_data(self.env)
        if not url or not token:
            return

        # TODO: Rotate MRs based on last checked
        merge_requests: MergeRequest = self.search([("state", "!=", "merged")], limit=limit)
        _logger.info("Reviewing %d merge requests for pruning", len(merge_requests))
        if not merge_requests:
            return

        pruned_mrs = self.browse([])
        client = ForwardbotClient(url, token, timeout)
        for merge_request in merge_requests:
            if merge_request.target_branch in merge_request.target_project_id.protected_branches:
                response = client.update_merge_request(
                    merge_request.target_project_id.remote_id,
                    merge_request.project_iid,
                    {"remove_source_branch": False},
                )
                _logger.info("Successfully cleared 'remove_source_branch' on %s", merge_request)
                if response.status_code != 200:
                    _logger.info("Failed clear 'remove_source_branch' on %s", merge_request)

                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            else:
                pruned_mrs |= merge_request

        _logger.info("Pruning merge requests")
        pruned_mrs.unlink()

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

        pending_for_fw: MergeRequest = self.search(
            [
                ("processed", "=", False),
                ("state", "in", states),
            ],
            limit=limit,
            order="id",
        )
        _logger.info("Will process %d MRs waiting for a forward port", len(pending_for_fw))
        if not pending_for_fw:
            return

        client = ForwardbotClient(url, token, timeout)
        for merge_request in pending_for_fw:
            try:
                merge_request.create_forward_port()
                forward_port = merge_request.forward_port_id
                if not forward_port:
                    _logger.info(
                        "No stable branch after %s for project %d. Forward port chain stopped",
                        merge_request.target_branch,
                        merge_request.target_project_id.remote_id,
                    )
                    response = client.delete_branch(merge_request.source_project_id, merge_request.source_branch)
                    if response.status_code not in [204, 404]:
                        _logger.warning("Received status code %d while deleting source branch %s")

                    merge_request.processed = True
                    continue

                _logger.info("Forward port %s created", forward_port)

                # Clone branch used for forward port
                response = client.create_branch(
                    forward_port.source_project_id, forward_port.source_branch, merge_request.source_branch
                )
                if response.status_code == 400:
                    message = response.json().get("message", "unknown")
                    if message != "Branch already exists":
                        _logger.warning("Branch creation failed with message %s", message)
                        continue
                elif response.status_code != 201:
                    _logger.warning(
                        "Received status code %d while cloning branch %s",
                        response.status_code,
                        merge_request.source_branch,
                    )
                    continue
                _logger.info(
                    "Successfully created forward port branch %s from %s",
                    forward_port.source_branch,
                    merge_request.source_branch,
                )

                # Delete original source branch
                response = client.delete_branch(merge_request.source_project_id, merge_request.source_branch)
                if response.status_code not in [204, 404]:
                    _logger.warning("Received status code %d while deleting source branch %s")
                    continue
                _logger.info("Deleted merged branch")

                # Create merge request (forward port)
                response = client.push_forward_port(merge_request)
                if response.status_code not in [200, 201]:
                    _logger.warning(
                        "Received status code %d when creating forward port for %s",
                        response.status_code,
                        merge_request,
                    )
                    continue

                data = response.json()
                merge_request.forward_port_id.write(
                    {
                        "global_id": data["id"],
                        "project_iid": data["iid"],
                        "state": data["state"],
                    }
                )
                merge_request.processed = True
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception as ex:
                _logger.warning("Exception %s occurred", ex)
                continue

            _logger.info(
                "Forward port %s successfully pushed to Gitlab",
                merge_request.forward_port_id,
            )
