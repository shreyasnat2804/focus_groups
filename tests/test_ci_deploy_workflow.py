"""Tests validating the CI/CD workflow YAML has correct deploy jobs."""

import yaml
import pathlib
import pytest

WORKFLOWS_DIR = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"
CI_PATH = WORKFLOWS_DIR / "ci.yml"


@pytest.fixture
def ci_workflow():
    """Load and parse the CI workflow YAML."""
    with open(CI_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def ci_jobs(ci_workflow):
    return ci_workflow["jobs"]


class TestDeployJobsExist:
    def test_deploy_api_job_exists(self, ci_jobs):
        assert "deploy-api" in ci_jobs, "deploy-api job missing from ci.yml"

    def test_deploy_web_job_exists(self, ci_jobs):
        assert "deploy-web" in ci_jobs, "deploy-web job missing from ci.yml"


class TestDeployJobsDependOnTest:
    def test_deploy_api_needs_test(self, ci_jobs):
        needs = ci_jobs["deploy-api"]["needs"]
        if isinstance(needs, list):
            assert "test" in needs
        else:
            assert needs == "test"

    def test_deploy_web_needs_test(self, ci_jobs):
        needs = ci_jobs["deploy-web"]["needs"]
        if isinstance(needs, list):
            assert "test" in needs
        else:
            assert needs == "test"


class TestWorkloadIdentityFederation:
    """Both deploy jobs must use WIF auth (id-token: write permission + auth action)."""

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_id_token_write_permission(self, ci_jobs, job_name):
        perms = ci_jobs[job_name].get("permissions", {})
        assert perms.get("id-token") == "write", (
            f"{job_name} must have id-token: write for WIF"
        )

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_uses_google_auth_action(self, ci_jobs, job_name):
        steps = ci_jobs[job_name]["steps"]
        auth_steps = [
            s for s in steps
            if s.get("uses", "").startswith("google-github-actions/auth@")
        ]
        assert len(auth_steps) >= 1, f"{job_name} must use google-github-actions/auth"

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_auth_uses_wif_secrets(self, ci_jobs, job_name):
        steps = ci_jobs[job_name]["steps"]
        auth_step = next(
            s for s in steps
            if s.get("uses", "").startswith("google-github-actions/auth@")
        )
        with_block = auth_step.get("with", {})
        wif_provider = with_block.get("workload_identity_provider", "")
        service_account = with_block.get("service_account", "")
        assert "WIF_PROVIDER" in wif_provider, "Must reference WIF_PROVIDER secret"
        assert "WIF_SERVICE_ACCOUNT" in service_account, "Must reference WIF_SERVICE_ACCOUNT secret"


class TestArtifactRegistryPush:
    """Both deploy jobs must push Docker images to Artifact Registry."""

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_configures_docker_for_artifact_registry(self, ci_jobs, job_name):
        steps = ci_jobs[job_name]["steps"]
        configure_steps = [
            s for s in steps
            if "configure-docker" in s.get("run", "") and "docker.pkg.dev" in s.get("run", "")
        ]
        assert len(configure_steps) >= 1, (
            f"{job_name} must configure Docker for Artifact Registry"
        )

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_pushes_image(self, ci_jobs, job_name):
        steps = ci_jobs[job_name]["steps"]
        push_steps = [
            s for s in steps
            if "docker push" in s.get("run", "")
        ]
        assert len(push_steps) >= 1, f"{job_name} must push Docker image"


class TestCloudRunDeploy:
    """Both deploy jobs must deploy to Cloud Run."""

    @pytest.mark.parametrize("job_name", ["deploy-api", "deploy-web"])
    def test_deploys_to_cloud_run(self, ci_jobs, job_name):
        steps = ci_jobs[job_name]["steps"]
        deploy_steps = [
            s for s in steps
            if "gcloud run deploy" in s.get("run", "")
        ]
        assert len(deploy_steps) >= 1, f"{job_name} must deploy to Cloud Run"

    def test_api_deploys_correct_service(self, ci_jobs):
        steps = ci_jobs["deploy-api"]["steps"]
        deploy_step = next(
            s for s in steps if "gcloud run deploy" in s.get("run", "")
        )
        assert "focusgroups-api" in deploy_step["run"]

    def test_web_deploys_correct_service(self, ci_jobs):
        steps = ci_jobs["deploy-web"]["steps"]
        deploy_step = next(
            s for s in steps if "gcloud run deploy" in s.get("run", "")
        )
        assert "focusgroups-web" in deploy_step["run"]
