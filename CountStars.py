#!/usr/bin/env python
"""
Count how many GitHub Stars a user has received, using GitHub API v4 GraphQL
"""
import requests
from pathlib import Path
import argparse

ENDPOINT = "https://api.github.com/graphql"


def run_query(query: str, token_file: Path):
    request = requests.post(ENDPOINT, json={"query": query}, headers={"Authorization": token_file.read_text()})
    if request.status_code == 200:
        return request.json()
    else:
        raise ValueError(f"Query failed with code {request.status_code}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("oauth", help="path to oauth key")
    p.add_argument("username", help="GitHub username(s) to count stars for", nargs="+")
    p = p.parse_args()

    query = """
query {
  search(type: REPOSITORY, user: %s query: "sort:stars stars:>1") {
    userCount
    edges {
      node {
        ... on Repository {
          name
          description
          stargazers {
            totalCount
          }
          url
        }
      }
    }
  }
}
    """ % (
        p.username
    )

    token_file = Path(p.oauth).expanduser()

    dat = run_query(query, token_file)
