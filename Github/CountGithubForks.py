#!/usr/bin/env python3

"""
lists all repos for a Github user.
Can use Oauth login.
GitHub API is otherwise very limited for unauthenticated users.

The Oauth file should be in a secure place, NOT in a Git repo!
Maybe encrypted and with permissions 600.
The Oauth key should have no checkboxes, so that it's read only for public repos.
"""

import pandas as pd
from argparse import ArgumentParser
import gitbulk.repo_stats as gu


def main():
    p = ArgumentParser(description="list all Github repos for a particular user")
    p.add_argument("user", help="Github username")
    p.add_argument("oauth", help="Oauth filename", nargs="?")
    p.add_argument("-b", "--branch", help="branch to consider")
    p.add_argument("-stars", help="only get star count", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p = p.parse_args()

    dat, ahead = gu.repo_prober(p.user, p.oauth, p.branch, p.stars, p.verbose)

    datnz = dat[~(dat == 0).all(axis=1)].drop_duplicates()
    # %%  Stars and Forks
    pd.set_option("display.max_rows", 500)

    print(f'\n{p.user} total stars received {datnz["stars"].sum()}')
    print(f'{p.user} total other users forked {datnz["forks"].sum()}\n')

    print(datnz.sort_values(["stars", "forks"], ascending=False))
    # %% Forks ahead
    if ahead:
        print(f"\n{p.user} Forks that are ahead by N commits")
        for a in ahead:
            print(a)


if __name__ == "__main__":
    main()
