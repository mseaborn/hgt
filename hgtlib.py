
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


def get_patches():
    start_point = None
    patches = []
    for line in open(get_patchlist_file(), "r"):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        ty, rest = line.split(" ", 1)
        if ty == "Patch":
            commit_id, msg = rest.split(" ", 1)
            patches.append({"commit_id": commit_id,
                            "msg": msg})
        elif ty == "Start":
            assert start_point is None
            start_point = rest
        else:
            raise Exception("Unknown tag: %r" % ty)
    assert start_point is not None
    return patches, start_point


def get_applylist():
    filename = os.path.join(dotgit_dir(), "hgt-applylist")
    data = {}
    for line in open(filename, "r"):
        tag, commit_id, rest = line.split(" ", 2)
        do_apply = {"Apply": True,
                    "Unapply": False}[tag]
        assert commit_id not in data
        data[commit_id] = do_apply
    return data
