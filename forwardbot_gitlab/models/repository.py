import logging
import re
from typing import List, Sequence
from urllib.parse import urljoin

from odoo import api, fields, models
from requests import Session

from ..api import get_api_data

_logger = logging.getLogger(__name__)


class Repository(models.Model):
    _name = "forwardbot_gitlab.repository"
    _description = "Gitlab Project (repository, fwbot)"
    _branch_version_regex = re.compile(r"(\d{2}(.\d)?)$")

    remote_id = fields.Integer(required=True)
    stable_branches = fields.Char()

    @api.model
    def get_branch_version(self, branch_name: str) -> float:
        """Obtain the version from a branch (if available) and return its value.
        Note: main/master are considered the newest version (they have a version value of 1000)
        """
        if (branch_name == "main") or (branch_name == "master"):
            return 1000.0

        version = self._branch_version_regex.search(branch_name)
        if version:
            return float(version[0])

        return -1.0

    def get_next_branch(self, branch_name: str) -> str:
        """Return the branch that follows the current one or an empty string if no branch exists after the
        current one. Only branches that exist in the current repository will be returned.

        For example, if a repository has branches 14.0 and 16.0, the branch that follows 14.0 is 16.0
        If the repo had a 15.0 branch, it would follow after 14.0 instead.
        """
        self.ensure_one()
        if not self.stable_branches:
            return ""
        branches = self.stable_branches.split(",")
        try:
            index = branches.index(branch_name)
            return branches[index + 1]
        except (IndexError, ValueError):
            return ""

    def update_branches(self, branches: List[str]):
        branches.sort(key=self.get_branch_version)
        self.stable_branches = ",".join(branches)

    @api.model
    def update_repository_branches(self, auto_commit=True, limit=50):
        url, token = get_api_data(self.env)
        if not url or not token:
            return

        # TODO: Rotate repos based on last sync time
        repositories: Sequence["Repository"] = self.search([], limit=limit, order="id")
        _logger.info(
            "Will update stable branches for %d repositories", len(repositories)
        )
        if not repositories:
            return

        session = Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        for repo in repositories:
            response = session.request(
                "GET", urljoin(url, f"/projects/{repo.remote_id}/repository/branches")
            )
            if response.status_code != 200:
                _logger.warning(
                    "Received status code %d when attempting to sync repository branches"
                )
            try:
                payload = response.json()
                branches = [branch["name"] for branch in payload]
                repo.update_branches(branches)

                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception as ex:
                _logger.warning("Exception %s occurred while processing %s", ex, repo)
                continue

            _logger.info("Branches for %s updated", repo)
