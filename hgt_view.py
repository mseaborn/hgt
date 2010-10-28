#!/usr/bin/env python

import os
import subprocess
import sys

import gtk

import hgt_view
import hgtlib


def get_git_config(git_dir, key):
    proc = subprocess.Popen(["git", "config", key], stdout=subprocess.PIPE)
    stdout = proc.communicate()[0]
    assert proc.wait() in (0, 1)
    return stdout.rstrip("\n")


def make_widget(do_reload, git_dir):
    rows, start_point = hgtlib.get_patches()
    applylist = hgtlib.get_applylist()

    model = gtk.TreeStore(object)

    def add_element(parent, elt):
        elt["failing"] = False
        elt["review"] = ""
        if "commit_id" in elt:
            elt["apply_id"] = elt["commit_id"]
            elt["apply"] = applylist.setdefault(elt["apply_id"], True)
            model.append(parent, [elt])
        else:
            elt["apply_id"] = elt["group_id"]
            elt["apply"] = applylist.setdefault(elt["apply_id"], True)
            treeiter = model.append(parent, [elt])
            for child in elt["patches"]:
                add_element(treeiter, child)
            if get_git_config(git_dir, "branch.%s.rietveldclosed"
                              % elt["group_id"]) == "yes":
                elt["review"] = "Committed"
            elif get_git_config(git_dir, "branch.%s.rietveldissue"
                                % elt["group_id"]) != "":
                elt["review"] = "Uploaded"

    for row in rows:
        add_element(None, row)

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

    def get_applylist():
        # We return this as a list rather than a dictionary in order
        # to preserve the tree order.
        got = []

        def recurse(elt):
            got.append((elt["apply_id"], elt["apply"], elt.get("msg", "")))
            if "patches" in elt:
                for child in elt["patches"]:
                    recurse(child)

        for row in rows:
            recurse(row)
        return got

    def get_applylist_dict():
        return dict((apply_id, state)
                    for apply_id, state, msg in get_applylist())

    def save_applylist():
        hgtlib.save_applylist(hgtlib.dotgit_dir(), get_applylist())

    def apply_patches():
        patches = hgtlib.get_selected_patches(rows, get_applylist_dict())
        msg = hgtlib.apply_patches(start_point, patches,
                                   git_dir, show_conflict=False)
        label.set_text(msg)

    table = gtk.TreeView()
    table.set_model(model)
    col = gtk.TreeViewColumn("Patch list")
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
        label.set_text("Selection changed")
        model.row_changed(model.get_path(treeiter), treeiter)
    cell.connect("toggled", clicked)
    cell = gtk.CellRendererText()
    col.pack_start(cell)
    #col.add_attribute(cell, "text", 0)
    def get_msg(row):
        if "group_id" in row:
            return row["group_id"]
        else:
            msg = row["msg"]
            if row["failing"]:
                msg = "[CONFLICTING] " + msg
            return msg
    map_cell2(col, cell, [("text", get_msg), #lambda row: row["msg"]),
                          ("foreground", bg_colour)])
    table.append_column(col)
    table.set_level_indentation(20)

    col = gtk.TreeViewColumn("Status")
    cell = gtk.CellRendererText()
    col.pack_start(cell)
    map_cell(col, cell, "text", lambda row: row["review"])
    table.append_column(col)

    scrolled = gtk.ScrolledWindow()
    scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled.add(table)

    checkout_button = gtk.Button("Check out selection")
    checkout_button.connect("clicked", lambda widget: apply_patches())
    reload_button = gtk.Button("Reload")
    reload_button.connect("clicked", lambda widget: do_reload())
    label = gtk.Label("Loaded patch list")
    hbox = gtk.HBox()
    hbox.pack_start(checkout_button, expand=False)
    hbox.pack_start(reload_button, expand=False)
    hbox.pack_start(label, expand=False, padding=10)
    vbox = gtk.VBox()
    vbox.pack_start(hbox, expand=False)
    vbox.add(scrolled)
    vbox.show_all()
    return vbox


def main(args):
    if len(args) == 0:
        git_dir = os.getcwd()
    elif len(args) == 1:
        git_dir = args[0]
    else:
        raise Exception("Too many arguments")

    window = gtk.Window()
    window.set_default_size(600, 800)
    window.set_title("Patch picker")
    window.connect("hide", lambda *args: sys.exit(0))

    def add_widget():
        window.add(hgt_view.make_widget(do_reload, git_dir))

    def do_reload():
        print "Reloading"
        reload(hgt_view)
        reload(hgtlib)
        for widget in window.get_children():
            widget.destroy()
        add_widget()

    add_widget()
    window.show()
    gtk.main()


if __name__ == "__main__":
    main(sys.argv[1:])
