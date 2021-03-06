"""
GitHub API utilities
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import logging
import typing as T
import pandas

import github


def check_api_limit(g: github.Github = None) -> None:
    """
    https://developer.github.com/v3/#rate-limiting
    don't hammer the API, avoiding 502 errors

    No penalty for checking rate limits

    Parameters
    ----------
    g : optional
        GitHub session
    """
    if g is None:
        g = session()

    api_limits = g.rate_limiting  # remaining, limit
    api_remaining, api_max = api_limits
    treset = datetime.utcfromtimestamp(g.rate_limiting_resettime)  # local time

    if api_remaining == 0:
        raise ConnectionRefusedError(
            f"GitHub rate limit exceeded: {api_remaining} / {api_max}. Try again after {treset} UTC."
        )
    # it's not elif !
    if api_remaining < 10:
        logging.warning(
            ResourceWarning(
                f"approaching GitHub API limit, {api_remaining} / {api_max} remaining until {treset} UTC."
            )
        )
    else:
        logging.info(f"GitHub API limit: {api_remaining} / {api_max} remaining until {treset} UTC.")


def session(oauth: Path = None) -> github.Github:
    """
    setup Git remote session

    Parameters
    ----------

    oauth : pathlib.Path, optional
        file containing Oauth hash

    Results
    -------
    g : github.Github
        Git remote session handle
    """
    if oauth:
        oauth = Path(oauth).expanduser()
        g = github.Github(oauth.read_text().strip())  # no trailing \n allowed
    else:  # unauthenticated
        g = github.Github()

    return g


def connect(
    oauth: Path, orgname: str = None
) -> tuple[
    github.AuthenticatedUser.AuthenticatedUser | github.Organization.Organization, github.Github
]:
    """
    retrieve organizations or users

    Parameters
    ----------
    oauth : pathlib.Path
        file containing Oauth hash
    orgname : str
        organization name or username

    Results
    -------
    op : github.AuthenticatedUser.AuthenticatedUser or github.Organization.Organization
        handle to organization or user
    sess : github.Github
        Git remote session
    """
    sess = session(oauth)
    guser = sess.get_user()

    org = None
    if orgname:
        assert isinstance(guser, github.AuthenticatedUser.AuthenticatedUser)
        orgs = list(guser.get_orgs())
        for o in orgs:
            if o.login == orgname:
                org = o
                break

        if org is None:
            raise ValueError(f"Organization {org} authentication could not be established")
        op = org
    else:
        assert isinstance(guser, github.Organization.Organization)
        op = guser

    return op, sess


def repo_exists(user: github.AuthenticatedUser.AuthenticatedUser, repo_name: str) -> bool:
    """
    Does a particular GitHub repo exist?

    Parameters
    ----------
    user : github.AuthenticatedUser.AuthenticatedUser or github.Organization.Organization
        GitHub user or organizaition handle
    repo_name : str
        repo_name under user

    Results
    -------
    exists : bool
        GitHub repo exists
    """
    exists = False
    try:
        repo = user.get_repo(repo_name)
        if repo.name:
            exists = True
    except github.GithubException as e:
        logging.info(str(e))

    return exists


def team_exists(user: github.AuthenticatedUser.AuthenticatedUser, team_name: str) -> bool:
    """
    Does a particular GitHub team exist?

    Parameters
    ----------
    user : github.AuthenticatedUser.AuthenticatedUser or github.Organization.Organization
        GitHub user or organizaition handle
    team_name : str
        team name

    Results
    -------
    exists : bool
        GitHub team exists
    """
    exists = False
    try:
        teams = user.get_teams()
        names = [t.name for t in teams]
        exists = team_name in names
    except github.GithubException as e:
        logging.info(str(e))

    return exists


def last_commit_date(sess: github.Github, name: str) -> datetime:
    """
    What is the last commit date to this repo.

    Equivalent to:

        git show -s --format=%cI HEAD


    Parameters
    ----------
    sess : github.Github
        GitHub session
    name : str
        name of GitHub repo e.g. pymap3d

    Results
    -------
    time : datetime.datetime
        time of last repo modification
    """
    time = None

    try:
        repo = sess.get_repo(name)
        if not repo_isempty(repo):
            time = repo.pushed_at
    except github.GithubException as e:
        logging.error(f"{name} not found \n")
        logging.info(str(e))

    return time


def repo_isempty(repo: github.Repository.Repository) -> bool:
    """
    is a GitHub repo empty?

    Parameters
    ----------
    repo : github.Repository
        handle to GitHub repo

    Results
    -------
    empty : bool
        GitHub repo empty
    """
    try:
        repo.get_contents("/")
        empty = False
    except github.GithubException as e:
        logging.error(f"{repo.name} is empty. \n")
        empty = True
        logging.info(str(e))

    return empty


def user_or_org(g: github.Github, user: str) -> T.Any:
    """
    Determines if user is a GitHub organization or standard user.
    This is relevant to getting private repos.

    Parameters
    ----------
    g: github.Github
        Github session handle
    user: str
        username or organization name

    Returns
    -------
    h: github.NamedUser.NamedUser or github.Organization.Organization
        the handle to the Organization or Username.
    """
    try:
        list(g.search_users(f"user:{user}"))
    except github.GithubException as e:
        raise ValueError(f"{user} not found on GitHub\n{e}")

    try:
        return g.get_organization(user)
    except github.GithubException:
        return g.get_user(user)


def read_repos(fn: Path, sheet: str) -> dict[str, str]:
    """
    make pandas.Series of email/id, Git url from spreadsheet

    Parameters
    ----------
    fn : pathlib.Path
        path to Excel spreadsheet listing usernames and repos to duplicate
    sheet : str
        name of Excel sheet to use

    Results
    -------
    repos : dict
        all the repos to duplicate
    """

    # %% get list of repos to duplicate
    fn = Path(fn).expanduser()
    repos = pandas.read_excel(fn, sheet_name=sheet, index_col=0, usecols="A, D").squeeze()
    repos.dropna(how="any", inplace=True)

    return repos.to_dict()


def get_repos(userorg: github.NamedUser.NamedUser) -> T.Iterable[github.Repository.Repository]:
    """
    get list of Repositories for a user or organization

    Parameters
    ----------
    userorg: github.NamedUser.NamedUser or github.Organization.Organization
        username or organization handle

    Returns
    -------
    repos: list of github.Repository
        all repos for a username / orgname

    https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#list-repositories-for-the-authenticated-user--parameters
    """
    return userorg.get_repos(type="all")
