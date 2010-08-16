
import os
import subprocess
import sys
import time

import gtk

import hgtlib


def main(args):
    if len(args) == 0:
        git_dir = os.getcwd()
    elif len(args) == 1:
        git_dir = args[0]
    else:
        raise Exception("Too many arguments")

    window = gtk.Window()
    window.set_default_size(600, 800)

    rows, start_point = hgtlib.get_patches()
    applylist = hgtlib.get_applylist()

    model = gtk.ListStore(object)
    for row in rows:
        row["apply"] = applylist.setdefault(row["commit_id"], True)
        row["failing"] = False
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

    def save_applylist():
        filename = os.path.join(hgtlib.dotgit_dir(), "hgt-applylist")
        tmp_filename = "%s.new" % filename
        fh = open(tmp_filename, "w")
        for row in rows:
            tag = {True: "Apply",
                   False: "Unapply"}[row["apply"]]
            fh.write("%s %s %s\n" % (tag, row["commit_id"], row["msg"]))
        fh.close()
        os.rename(tmp_filename, filename)

    def apply_patches():
        t0 = time.time()

        proc = subprocess.Popen(["git", "diff", "HEAD"], cwd=git_dir,
                                stdout=subprocess.PIPE)
        stdout = proc.communicate()[0]
        if stdout != "":
            print "Uncommitted changes (tree does not match HEAD) - aborting"
            return

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
                    # Get the working copy out of the conflict state.
                    subprocess.check_call(["git", "reset", "--hard"],
                                          cwd=git_dir)
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
        treeiter = model.get_iter(path)
        row = model.get_value(treeiter, 0)
        row["apply"] = not row["apply"]
        save_applylist()
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

    scrolled = gtk.ScrolledWindow()
    scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled.add(table)

    checkout_button = gtk.Button("Check out selection")
    checkout_button.connect("clicked", lambda widget: apply_patches())
    hbox = gtk.HBox()
    hbox.pack_start(checkout_button, expand=False)
    vbox = gtk.VBox()
    vbox.pack_start(hbox, expand=False)
    vbox.add(scrolled)

    window.add(vbox)
    window.show_all()
    window.connect("hide", lambda *args: sys.exit(0))
    gtk.main()


if __name__ == "__main__":
    main(sys.argv[1:])
