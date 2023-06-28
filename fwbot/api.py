import re
from typing import TYPE_CHECKING, Dict
from urllib.parse import quote, urljoin

from requests import Request, Response, Session

if TYPE_CHECKING:
    from .models.merge_request import MergeRequest

_footer_regex = re.compile(r"This is an automatic forward port for !\d+$")


def get_api_data(env):
    config = env["ir.config_parameter"].sudo()
    token = config.get_param("fwbot.token")
    url = config.get_param("fwbot.base_url")

    return url, token


class ForwardbotGitlabClient(Session):
    def __init__(self, url: str, token: str, timeout: int = 10):
        super().__init__()

        self._url = urljoin(url, "api/v4/")
        self._token = token
        self._timeout = timeout
        self.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, *args, **kwargs) -> Response:
        kwargs.setdefault("timeout", self._timeout)
        return super().request(*args, **kwargs)

    def get_protected_branches(self, project_id: int) -> Response:
        return self.get(urljoin(self._url, f"projects/{project_id}/protected_branches"))

    def push_forward_port(self, merge_request: "MergeRequest") -> Response:
        forward_port = merge_request.forward_port_id
        if _footer_regex.search(forward_port.description):
            description = re.sub(
                _footer_regex,
                forward_port.description,
                f"This is an automatic forward port for !{merge_request.internal_id}",
            )
        else:
            description = (
                forward_port.description
                + f"\n\n---\nThis is an automatic forward port for !{merge_request.internal_id}"
            )

        request = Request(
            "POST",
            urljoin(
                self._url,
                f"projects/{forward_port.target_repository_id.remote_id}/merge_requests",
            ),
            json={
                "id": forward_port.source_repository_id.remote_id,
                "source_branch": forward_port.source_branch,
                "target_branch": forward_port.target_branch,
                "title": forward_port.name,
                "description": description,
            },
            headers={"Content-Type": "application/json"},
        )
        prepared_request = self.prepare_request(request)

        return self.send(prepared_request, timeout=self._timeout)

    def update_merge_request(self, project_id: int, merge_iid: int, payload: Dict) -> Response:
        return self.put(
            urljoin(self._url, f"projects/{project_id}/merge_requests/{merge_iid}"),
            json=payload,
        )

    def create_branch(self, project_id: int, name: str, ref: str) -> Response:
        return self.post(
            urljoin(self._url, f"projects/{project_id}/repository/branches"),
            json={"branch": name, "ref": ref},
        )

    def delete_branch(self, project_id: int, name: str) -> Response:
        return self.delete(urljoin(self._url, quote(f"projects/{project_id}/repository/branches/{name}")))
