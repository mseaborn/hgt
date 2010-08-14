
import subprocess
import sys
import time

import gtk

import hgtlib


def get_patches():
    start_point = None
    patches = []
    for line in open(hgtlib.get_patchlist_file(), "r"):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        ty, rest = line.split(" ", 1)
        if ty == "Patch":
            patches.append(rest.split(" ", 1))
        elif ty == "Start":
            assert start_point is None
            start_point = rest
        else:
            raise Exception("Unknown tag: %r" % ty)
    assert start_point is not None
    return patches, start_point


def main(args):
    git_dir = args[0]

    window = gtk.Window()
    window.set_default_size(500, 400)

    commits, start_point = get_patches()

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

        # This is just to let us delete the "cp" branch.
        subprocess.check_call(["git", "checkout", start_point], cwd=git_dir)

        subprocess.call(["git", "branch", "-D", "cp"], cwd=git_dir)
        subprocess.check_call(["git", "checkout", "-b", "cp", start_point],
                              cwd=git_dir)
        for row in rows:
            row["failing"] = False
        for row in rows:
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
    window.connect("hide", lambda *args: sys.exit(0))
    gtk.main()


if __name__ == "__main__":
    main(sys.argv[1:])
