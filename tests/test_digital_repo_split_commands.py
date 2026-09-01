from masck_one.digital_release import load_repo_split_config


def test_future_digital_repositories_require_real_build_and_test_commands():
    config = load_repo_split_config()
    workspaces = config["workspaces"]

    assert set(workspaces) == {"web", "app"}
    for workspace_name in ("web", "app"):
        workspace = workspaces[workspace_name]
        assert workspace["build_command"] == "npm run build"
        assert workspace["test_command"] == "npm test"
        assert "--if-present" not in workspace["test_command"]
