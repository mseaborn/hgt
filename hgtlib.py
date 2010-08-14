
import os


def dotgit_dir():
    git_dir = os.getcwd()
    while True:
        dotgit = os.path.join(git_dir, ".git")
        if os.path.exists(dotgit):
            return dotgit
        assert git_dir != "/"
        git_dir = os.path.dirname(git_dir)


def get_patchlist_file():
    patchlist_file = os.path.join(dotgit_dir(), "hgt-patches")
    if not os.path.exists(patchlist_file):
        raise Exception("HGT not initialised in this repo")
    return patchlist_file
