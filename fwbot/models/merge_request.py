import logging
from typing import Any, Dict, Sequence, Tuple

from odoo import api, fields, models
from requests import Response

from ..api import ForwardbotGitlabClient, get_api_data
from .repository import Repository

_logger = logging.getLogger(__name__)


class MergeRequest(models.Model):
    _name = "fwbot.merge.request"
    _description = "Merge Request (fwbot)"
    _inherit = "fwbot.remote.mixin"

    name = fields.Char(help="Merge Request Title", required=True)
    description = fields.Text()
    global_id = fields.Integer(help="ID for this MR on the remote server. Unique across all projects")
    internal_id = fields.Integer(help="Internal ID. Unique inside the target project.")
    source_branch = fields.Char(required=True)
    source_repository_id: Repository = fields.Many2one("fwbot.repository", required=True)
    target_branch = fields.Char(required=True)
    target_repository_id: Repository = fields.Many2one("fwbot.repository", required=True)
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
    forward_port_id: "MergeRequest" = fields.Many2one("fwbot.merge.request")
    processed = fields.Boolean(default=False)

    _sql_constraints = [
        (
            "unique_global_id",
            "UNIQUE (global_id)",
            "Two MRs can't have the same ID",
        ),
    ]

    def create_forward_port(self) -> "MergeRequest":
        self.ensure_one()
        if self.forward_port_id:
            return self.forward_port_id

        forward_branch = self.target_repository_id.get_next_branch(self.target_branch)
        source_branch = f"{forward_branch}-forward{self.internal_id}-fwb{self.id}"
        name = self.name
        if not self.name.startswith("[FW]"):
            if self.name.startswith("["):
                name = f"[FW]{name}"
            else:
                name = f"[FW] {name}"

        self.forward_port_id = self.create(
            {
                "name": name,
                "description": self.description,
                "source_repository_id": self.source_repository_id.id,
                "source_branch": source_branch,
                "target_repository_id": self.target_repository_id.id,
                "target_branch": forward_branch,
            }
        )

        return self.forward_port_id

    def update_from_object_attributes(self, object_attributes: Dict[str, Any]):
        self.ensure_one()
        self.write(
            {
                "name": object_attributes["title"],
                "state": object_attributes["state"],
                "description": object_attributes.get("description"),
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
    def gitlab_obtain_from_event(self, data: Dict) -> Tuple["MergeRequest", bool]:
        """Obtain (search and create if not found) a record based on the data
        provided by a Merge Request event as described by Gitlab on:
        https://docs.gitlab.com/ee/user/project/integrations/webhook_events.html#merge-request-events
        """
        data_object = data["object_attributes"]

        merge_request = self.search([("global_id", "=", data_object["id"])])
        if merge_request:
            return merge_request, False

        target_repository_id = data_object["target_project_id"]
        target_project = self.env["fwbot.repository"].search([("remote_id", "=", target_repository_id)], limit=1)
        if not target_project:
            target_project = self.env["fwbot.repository"].create(
                {
                    "name": data_object["target"]["path_with_namespace"],
                    "url": data_object["target"]["web_url"],
                    "remote_id": target_repository_id,
                    "platform": "gitlab",
                }
            )

        source_project_id = data_object["source_project_id"]
        source_project = self.env["fwbot.repository"].search([("remote_id", "=", source_project_id)], limit=1)
        if not source_project:
            source_project = self.env["fwbot.repository"].create(
                {
                    "name": data_object["source"]["path_with_namespace"],
                    "url": data_object["source"]["web_url"],
                    "remote_id": source_project_id,
                    "platform": "gitlab",
                }
            )

        return (
            self.env["fwbot.merge.request"].create(
                {
                    "name": data_object["title"],
                    "description": data_object.get("description"),
                    "source_branch": data_object["source_branch"],
                    "source_repository_id": source_project.id,
                    "target_branch": data_object["target_branch"],
                    "target_repository_id": target_project.id,
                    "global_id": data_object["id"],
                    "internal_id": data_object["iid"],
                    "state": data_object["state"],
                }
            ),
            True,
        )

    def remove_source_branch(self):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.source_repository_id.platform}_remove_source_branch")

        return platform_method()

    def _gitlab_remove_source_branch(self):
        self.ensure_one()
        url, token = self.source_repository_id.get_api_data()
        response = ForwardbotGitlabClient(
            url,
            token,
        ).delete_branch(self.source_repository_id.remote_id, self.source_branch)
        if response.status_code != 404:
            response.raise_for_status()

    def update_merge_request(self, payload: Dict):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_update_merge_request")

        return platform_method(payload)

    def _gitlab_update_merge_request(self, payload: Dict):
        self.ensure_one()
        url, token = self.target_repository_id.get_api_data()
        response = ForwardbotGitlabClient(url, token, self.timeout).update_merge_request(
            self.target_repository_id.remote_id, self.internal_id, payload
        )
        response.raise_for_status()

    def push_forward_port(self, forward_port: "MergeRequest"):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_push_forward_port")

        return platform_method(forward_port)

    def _gitlab_push_forward_port(self, forward_port: "MergeRequest") -> Response:
        self.ensure_one()
        url, token = self.target_repository_id.get_api_data()

        return ForwardbotGitlabClient(url, token, self.timeout).push_forward_port(forward_port)

    @api.model
    def prune_merge_requests(self, auto_commit=False, limit=50, timeout=10):
        merge_requests = self
        if not merge_requests:
            merge_requests: MergeRequest = self.search(
                [("state", "!=", "merged")], limit=limit, order="last_processed ASC"
            )
        _logger.info("Reviewing %d merge requests for pruning", len(merge_requests))
        if not merge_requests:
            return

        pruned_mrs = self.browse([])
        for merge_request in merge_requests:
            if merge_request.target_branch in (merge_request.target_repository_id.stable_branches or []):
                try:
                    merge_request.with_context({"timeout": timeout}).update_merge_request(
                        {"remove_source_branch": False}
                    )

                    _logger.info("Successfully cleared 'remove_source_branch' on %s", merge_request)
                except Exception as ex:
                    _logger.info("%s while clearing 'remove_source_branch' on %s", ex, merge_request)
                finally:
                    merge_request.last_processed = fields.Datetime.now()
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
        _logger.info("Will process %d MR(s) waiting for a forward port", len(pending_for_fw))
        if not pending_for_fw:
            return

        for merge_request in pending_for_fw:
            try:
                merge_request = merge_request.with_context({"timeout": timeout})
                merge_request.create_forward_port()
                forward_port = merge_request.forward_port_id
                _logger.info("Forward port %s created", forward_port)

                # Clone branch used for forward port
                response = merge_request.source_repository_id.clone_branch(
                    forward_port.target_branch,
                    forward_port.source_branch,
                )
                if response.status_code == 400:
                    message = response.json().get("message", "unknown")
                    if message != "Branch already exists":
                        response.raise_for_status()
                else:
                    response.raise_for_status()

                # Gather merge request commits
                # TODO...

                # git cherry-pick
                # TODO...

                # Delete original source branch
                merge_request.remove_source_branch()

                # Create merge request (forward port)
                response = merge_request.push_forward_port(merge_request)
                response.raise_for_status()
                data = response.json()
                merge_request.forward_port_id.write(
                    {
                        "global_id": data["id"],
                        "internal_id": data["iid"],
                        "state": data["state"],
                    }
                )
                merge_request.processed = True
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception as ex:
                _logger.error("%s", ex)
                continue

            _logger.info(
                "Forward port %s successfully pushed",
                merge_request.forward_port_id,
            )
