
import StringIO
import os
import shutil
import subprocess
import tempfile
import unittest

import hgtlib


def read_file(filename):
    fh = open(filename, "r")
    try:
        return fh.read()
    finally:
        fh.close()


def write_file(filename, data):
    fh = open(filename, "w")
    try:
        fh.write(data)
    finally:
        fh.close()


# http://lackingrhoticity.blogspot.com/2008/11/tempdirtestcase-python-unittest-helper.html
class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        self._on_teardown = []

    def make_temp_dir(self):
        temp_dir = tempfile.mkdtemp(prefix="tmp-%s-" % self.__class__.__name__)
        def tear_down():
            shutil.rmtree(temp_dir)
        self._on_teardown.append(tear_down)
        return temp_dir

    def tearDown(self):
        for func in reversed(self._on_teardown):
            func()


class ParsingTest(unittest.TestCase):

    def test_parse(self):
        data = """
Start git-svn

# Comment (ignored)
Patch 1234 desc 1

Group group desc
{
  Patch 3456 grouped desc 1
  Patch 4567 grouped desc 2
}

Patch 2345 desc 2
"""
        patches, start = hgtlib.parse_file(StringIO.StringIO(data))
        expect = [
            {'commit_id': '1234', 'msg': 'desc 1'},
            {'group_id': 'group desc', 'patches': [
                 {'commit_id': '3456', 'msg': 'grouped desc 1'},
                 {'commit_id': '4567', 'msg': 'grouped desc 2'},
                 ]},
            {'commit_id': '2345', 'msg': 'desc 2'}]
        self.assertEquals(patches, expect)
        self.assertEquals(start, "git-svn")


test_revisions = [
    ("Initial commit", r"""
#include <stdio.h>

int main() {
  return 0;
}
"""),
    ("Add friendly message", r"""
#include <stdio.h>

int main() {
  printf("hello\n");
  return 0;
}
"""),
    ("Use standard message", r"""
#include <stdio.h>

int main() {
  printf("hello world\n");
  return 0;
}
"""),
]


class ToolTest(TempDirTestCase):

    def test(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = self.make_temp_dir()

        def run_cmd(args):
            env = os.environ.copy()
            env["PATH"] = "%s:%s" % (script_dir, env["PATH"])
            subprocess.check_call(args, cwd=temp_dir, env=env)

        run_cmd(["git", "init", "-q"])
        run_cmd(["hgt-init"])
        test_file = os.path.join(temp_dir, "hello.c")
        for i, (msg, data) in enumerate(test_revisions):
            write_file(test_file, data)
            run_cmd(["git", "add", "hello.c"])
            if i == 0:
                # Git treats the first commit specially.
                run_cmd(["git", "commit", "-m", "Initial revision"])
                run_cmd(["git", "tag", "git-svn"])
            else:
                run_cmd(["hgt-record", "-a", "-m", msg])

        # Test that hgt-checkout works, and that newly-recorded
        # patches are enabled by default.
        run_cmd(["hgt-checkout"])
        self.assertEquals(read_file(test_file), test_revisions[-1][1])

        patches_file = os.path.join(temp_dir, ".git", "hgt-patches")
        patches, start_point = hgtlib.parse_file(open(patches_file))
        # This assertion just tests the default.
        self.assertEquals(start_point, "git-svn")
        self.assertEquals([patch["msg"] for patch in patches],
                          ["Add friendly message",
                           "Use standard message"])

        grouped_patches = [{"group_id": "add-message",
                            "patches": patches}]
        write_patch_list(temp_dir, grouped_patches, start_point)
        before_id, after_id = hgtlib.get_before_and_after(
            temp_dir, "add-message")
        proc = subprocess.Popen(["git", "diff", before_id, after_id],
                                cwd=temp_dir, stdout=subprocess.PIPE)
        diff = proc.communicate()[0]
        self.assertEquals(proc.wait(), 0)
        diffs = [line for line in diff.split("\n")
                 if line.startswith("+")
                 and not line.startswith("+++ ")]
        self.assertEquals(diffs, ['+  printf("hello world\\n");'])

        # Test selection that causes a conflict.
        dotgit_dir = os.path.join(temp_dir, ".git")
        hgtlib.save_applylist(dotgit_dir,
                              [(patches[0]["commit_id"], False, "")])
        run_cmd(["hgt-checkout"])
        # Without -C, the working copy is left clean and there are no
        # conflict markers.
        self.assertEquals(read_file(test_file), test_revisions[0][1])
        # -C leaves in the conflict markers.
        run_cmd(["hgt-checkout", "-C"])
        proc = subprocess.Popen(["git", "diff"], cwd=temp_dir,
                                stdout=subprocess.PIPE)
        diff = proc.communicate()[0]
        self.assertEquals(proc.wait(), 0)
        diffs = [line for line in diff.split("\n")
                 if line.startswith("+")
                 and not line.startswith("+++ ")
                 and not "<<<<<<<" in line
                 and not ">>>>>>>" in line]
        self.assertEquals(diffs,
                          ['++=======',
                           '+   printf("hello world\\n");'])


def write_patch_list(git_dir, patches, start_point):
    filename = os.path.join(hgtlib.dotgit_dir(git_dir), "hgt-patches")
    fh = open(filename, "w")
    fh.write("Start %s\n" % start_point)

    def recurse(patches):
        for patch in patches:
            if "group_id" in patch:
                fh.write("Group %s\n{\n" % patch["group_id"])
                recurse(patch["patches"])
                fh.write("}\n")
            else:
                fh.write("Patch %s %s\n" % (patch["commit_id"], patch["msg"]))

    recurse(patches)
    fh.close()


if __name__ == "__main__":
    unittest.main()
