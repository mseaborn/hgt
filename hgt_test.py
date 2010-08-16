
import StringIO
import unittest

import hgtlib


class Test(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
