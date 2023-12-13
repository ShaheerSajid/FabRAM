#layer information metals and vias

#rules = width, spacing, area
import json
def create_rule(name, width, spacing):
    rules = {"name":name, "width":width, "spacing":spacing}
    return rules

def create_layer(name, purpose, layer, datatype):
    lay = {"name":name, "purpose":purpose, "layer":layer, "datatype":datatype}
    return lay

def create_cellmap(cell, name):
    cellmap = {"cell":cell, "name":name}
    return cellmap

def populate_layers(file):
    f = open(file,"r")
    lines = f.readlines()
    layers = {}
    for l in lines[1:]:
        l = l.split()
        layers[l[0]] = [int(l[1]), int(l[2])]
    return layers

def populate_rules(file):
    f = open(file,"r")
    lines = f.readlines()
    rules = {}
    for l in lines[1:]:
        l = l.split()
        if "VIA" in l[0]:
          via_encl = l[2].split(',')
          bot_encl = [float(via_encl[0]),float(via_encl[1])]
          top_encl = [float(via_encl[2]),float(via_encl[3])]
          rules[l[0]] = [float(l[1]),bot_encl,top_encl]
        else:
          rules[l[0]] = [float(l[1]), float(l[2])]
    return rules

def populate_names(file):
    f = open(file,"r")
    lines = f.readlines()
    names = {}
    for l in lines[1:]:
        l = l.split()
        names[l[0]] = l[1]
    return names
