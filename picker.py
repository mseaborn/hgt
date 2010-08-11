
import subprocess
import sys
import time

import gtk


def main(args):
    git_dir = args[0]

    window = gtk.Window()
    window.set_default_size(500, 400)

    proc = subprocess.Popen(["git", "log", "--pretty=oneline",
                             "master", "edit-conflict", "^initial"],
                            cwd=git_dir,
                            stdout=subprocess.PIPE)
    commits = []
    for line in proc.stdout:
        commits.append(line.rstrip("\n").split(" ", 1))
    assert proc.wait() == 0

    model = gtk.ListStore(object)
    rows = []
    for commit_id, desc in commits:
        row = {"commit_id": commit_id, "msg": desc, "apply": False,
               "failing": False}
        rows.append(row)
        model.append([row])

    def map_cell(col, cell, prop, func):
        def setter(col, cell, model, treeiter):
            row = model.get_value(treeiter, 0)
            cell.set_property(prop, func(row))
        col.set_cell_data_func(cell, setter)

    def map_cell2(col, cell, pairs):
        def setter(col, cell, model, treeiter):
            row = model.get_value(treeiter, 0)
            for prop, func in pairs:
                cell.set_property(prop, func(row))
        col.set_cell_data_func(cell, setter)

    def apply_patches():
        t0 = time.time()
        # XXX: This could lose work
        subprocess.check_call(["git", "reset", "--hard"], cwd=git_dir)

        subprocess.check_call(["git", "checkout", "initial"], cwd=git_dir)
        subprocess.call(["git", "branch", "-D", "cp"], cwd=git_dir)
        subprocess.check_call(["git", "checkout", "-b", "cp", "initial"],
                              cwd=git_dir)
        for row in rows:
            row["failing"] = False
        for row in reversed(rows):
            if row["apply"]:
                rc = subprocess.call(["git", "cherry-pick", row["commit_id"]],
                                     cwd=git_dir)
                if rc != 0:
                    row["failing"] = True
                    break
        t1 = time.time()
        print "took %.2fs" % (t1 - t0)

    table = gtk.TreeView()
    table.set_model(model)
    col = gtk.TreeViewColumn("")
    cell = gtk.CellRendererToggle()
    col.pack_start(cell, expand=False)
    #col.add_attribute(cell, "active", 1)
    def bg_colour(row):
        if row["failing"]:
            return "red"
    map_cell2(col, cell, [("active", lambda row: row["apply"]),
                          #("foreground", bg_colour)
                          ])
    def clicked(cell, path):
        print "clicked", path
        treeiter = model.get_iter(path)
        row = model.get_value(treeiter, 0)
        row["apply"] = not row["apply"]
        apply_patches()
        model.row_changed(model.get_path(treeiter), treeiter)

        treeiter = model.get_iter_root()
        model.row_changed(model.get_path(treeiter), treeiter)
    cell.connect("toggled", clicked)
    cell = gtk.CellRendererText()
    table.append_column(col)

    col = gtk.TreeViewColumn("Message")
    col.pack_start(cell)
    #col.add_attribute(cell, "text", 0)
    def get_msg(row):
        msg = row["msg"]
        if row["failing"]:
            msg = "[CONFLICTING] " + msg
        return msg
    map_cell2(col, cell, [("text", get_msg), #lambda row: row["msg"]),
                          ("foreground", bg_colour)])
    table.append_column(col)

    window.add(table)
    window.show_all()
    gtk.main()


if __name__ == "__main__":
    main(sys.argv[1:])
