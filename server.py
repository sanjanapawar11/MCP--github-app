import os

from dotenv import load_dotenv
from github import Github, GithubException
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("WorkSphere MCP")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_github_client():
    """Create a GitHub client using the configured personal access token."""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is missing. Add it to your .env file.")
    return Github(GITHUB_TOKEN)


@mcp.tool()
def list_repositories() -> str:
    """List up to 10 most recently updated repositories accessible to the authenticated GitHub user."""
    try:
        client = get_github_client()
        try:
            user = client.get_user()
            results = []

            for repo in user.get_repos(sort="updated")[:10]:
                results.append(
                    f"Name: {repo.full_name}\n"
                    f"URL: {repo.html_url}\n"
                    f"Description: {repo.description or 'No description'}\n"
                    f"Private: {repo.private}"
                )

            return "\n---\n".join(results) if results else "No repositories found."
        finally:
            client.close()

    except GithubException as error:
        return f"GitHub API error: {error}"
    except ValueError as error:
        return str(error)


@mcp.tool()
def get_repository_details(repo_name: str) -> str:
    """Get details of a repository owned by the authenticated GitHub user, using its repository name."""
    try:
        client = get_github_client()
        try:
            repo = client.get_user().get_repo(repo_name)
            return (
                f"Repository: {repo.full_name}\n"
                f"Description: {repo.description or 'No description'}\n"
                f"URL: {repo.html_url}\n"
                f"Stars: {repo.stargazers_count}\n"
                f"Forks: {repo.forks_count}\n"
                f"Language: {repo.language or 'Not specified'}\n"
                f"Default branch: {repo.default_branch}\n"
                f"Private: {repo.private}"
            )
        finally:
            client.close()

    except GithubException as error:
        return f"GitHub API error: {error}"
    except ValueError as error:
        return str(error)


if __name__ == "__main__":
    mcp.run(transport="stdio")
