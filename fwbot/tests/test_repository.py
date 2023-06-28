from unittest.mock import Mock, patch

from ..api import ForwardbotGitlabClient
from ..models.repository import Repository
from .common import ForwardBotCase, MockResponse


class TestRepository(ForwardBotCase):
    def test_get_branch_version(self):
        self.assertEqual(1000.0, self.model_repo.get_branch_version("main"))
        self.assertEqual(1000.0, self.model_repo.get_branch_version("master"))

        self.assertEqual(12.0, self.model_repo.get_branch_version("12.0"))
        self.assertEqual(12.0, self.model_repo.get_branch_version("saas-12"))

        self.assertEqual(16.1, self.model_repo.get_branch_version("16.1"))
        self.assertEqual(16.1, self.model_repo.get_branch_version("saas-16.1"))

        self.assertEqual(-1.0, self.model_repo.get_branch_version("bazinga"))

    def test_get_next_branch(self):
        project = self.model_repo.create(
            {
                "name": "rando",
                "url": "hey",
                "remote_id": 5,
                "stable_branches": "12.0,14.0,15.0,master",
                "platform": "gitlab",
            }
        )
        self.assertEqual("14.0", project.get_next_branch("12.0"))
        self.assertEqual("15.0", project.get_next_branch("14.0"))
        self.assertEqual("master", project.get_next_branch("15.0"))
        self.assertEqual("", project.get_next_branch("master"))

    def test_updated_branches(self):
        project = self.model_repo.create({"name": "timmy", "url": "turner", "remote_id": 4, "platform": "gitlab"})
        project.update_branches(["16.0", "master", "14.0", "12", "saas-12.1", "15.0", "13.0"])

        expected_list = ["12", "saas-12.1", "13.0", "14.0", "15.0", "16.0", "master"]
        self.assertEqual(",".join(expected_list), project.stable_branches)

    @patch(f"{__name__}.ForwardbotGitlabClient.get")
    def test_gitlab_sync_repository_branches(self, mock: Mock):
        mock.side_effect = lambda *_args: MockResponse(
            json_data=[{"name": "15.0"}, {"name": "21.0"}, {"name": "saas-12"}]
        )

        repo = self.model_repo.create(
            {
                "name": "paul",
                "remote_id": 12,
                "platform": "gitlab",
                "url": "https://git.vauxoo.local/paul/repo",
                "token": "letmein",
            }
        )
        repo.gitlab_sync_repository_branches()
        self.assertEqual("saas-12,15.0,21.0", repo.stable_branches)

        self.assertEqual(mock.call_count, 1)
        self.assertEqual("https://git.vauxoo.local/api/v4/projects/12/protected_branches", mock.call_args[0][0])
