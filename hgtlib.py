
import os
import subprocess
import time


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


def parse_group(iterable, handle_line):
    line = iterable.next()
    if line != "{":
        raise Exception("Expected '{'")
    while True:
        line = iterable.next()
        if line == "}":
            break
        handle_line(line)


def parse_elt(line, lines):
    ty, rest = line.split(" ", 1)
    if ty == "Patch":
        commit_id, msg = rest.split(" ", 1)
        return {"commit_id": commit_id, "msg": msg}
    elif ty == "Group":
        got = []
        def handle_line(line):
            elt = parse_elt(line, lines)
            assert "start" not in elt
            got.append(elt)
        parse_group(lines, handle_line)
        return {"group_id": rest, "patches": got}
    elif ty == "Start":
        return {"start": rest}
    else:
        raise Exception("Unknown tag: %r" % ty)


def parse_file(fh):
    def get_lines():
        for line in fh:
            line = line.strip()
            if line != "" and not line.startswith("#"):
                yield line

    got = []
    start_point = None
    lines = get_lines()
    for line in lines:
        elt = parse_elt(line, lines)
        if "start" in elt:
            assert start_point is None
            start_point = elt["start"]
        else:
            got.append(elt)
    return got, start_point


def get_patches():
    return parse_file(open(get_patchlist_file(), "r"))


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


def get_selected_patches(patches, applylist):
    got = []
    def recurse(elt):
        if "patches" in elt:
            apply_id = elt["group_id"]
        else:
            apply_id = elt["commit_id"]

        if applylist.get(apply_id, True):
            if "patches" in elt:
                for child in elt["patches"]:
                    recurse(child)
            else:
                got.append(elt)
    for elt in patches:
        recurse(elt)
    return got


def apply_patches(start_point, patches, git_dir, show_conflict,
                  dest_branch=None):
    if dest_branch is None:
        dest_branch = "cp"
    t0 = time.time()

    proc = subprocess.Popen(["git", "diff", "HEAD"], cwd=git_dir,
                            stdout=subprocess.PIPE)
    stdout = proc.communicate()[0]
    if stdout != "":
        return "Uncommitted changes (tree does not match HEAD) - aborting"

    # In case we are already on dest_branch, we need to switch away
    # from the branch.  Otherwise, if update-ref has made a change,
    # "git checkout dest_branch" will get confused because it will
    # think it nothing has changed because it is not switching branch.
    subprocess.check_call(["git", "checkout", start_point], cwd=git_dir)

    # Using update-ref rather than "git branch -D" avoids deleting the
    # reflog for the branch.
    subprocess.check_call(
        ["git", "update-ref", "-m", "HGT: Reset to start point",
         "refs/heads/%s" % dest_branch, start_point], cwd=git_dir)
    subprocess.check_call(["git", "checkout", dest_branch],
                          cwd=git_dir)
    failed = False
    for patch in patches:
        rc = subprocess.call(["git", "cherry-pick", patch["commit_id"]],
                             cwd=git_dir)
        if rc != 0:
            if not show_conflict:
                # Get the working copy out of the conflict state.
                subprocess.check_call(["git", "reset", "--hard"],
                                      cwd=git_dir)
            patch["failing"] = True
            failed = True
            break
    t1 = time.time()
    if failed:
        return "Got conflict when applying selection"
    else:
        return "Applied selection OK"
    print "took %.2fs" % (t1 - t0)
