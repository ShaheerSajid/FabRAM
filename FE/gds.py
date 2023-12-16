import math
import re
import gdspy
import glob
import tech

#array names
cell_prefix     = "bit_arr_"
mat_prefix      = "mat_arr_"
amp_prefix      = "se_arr_"
pchg_prefix     = "pchg_arr_"
dec_prefix      = "dec_arr_"
col_dec_prefix  = "cdec_arr_"
dido_prefix     = "dido_arr_"


def cell_get_dim(cell):
  dims = []
  llx = cell.get_bounding_box()[0][0]
  lly = cell.get_bounding_box()[0][1]
  urx = cell.get_bounding_box()[1][0]
  ury = cell.get_bounding_box()[1][1]
  dims.append([0, 0])
  dims.append([urx,ury])
  return dims

def get_lay_info(layer):
    print()

def get_via_info(cut): 
    print()


def gen_gds(mem_words, mem_bits, col_mux):
    #rows
    num_words = int(mem_words/col_mux)
    #columns
    num_bits = mem_bits*col_mux
    top_name        = 'sram'+str(mem_words)+'x'+str(mem_bits)

    row_bits    = math.log2(num_words)
    num_inputs  = math.ceil(math.log(num_words, 4))

    delay_val = 10
    ##############################################################
    # Generate GDS 
    ##############################################################
    layers      = tech.populate_layers("layermap.txt")
    rules       = tech.populate_rules("layerrules.txt")
    cellnames   = tech.populate_names("cellmap.txt")


    #topcell
    lib = gdspy.GdsLibrary(precision=5e-09)
    cell = lib.new_cell('sram_'+str(mem_words)+'x'+str(mem_bits))

    # read in all gds files
    for f in glob.glob("gds/*.gds"):
        lib.read_gds(infile=f)
    ########################################################
    # generate sram cell array
    ########################################################
    bit_arr_cell = lib.new_cell(name=cell_prefix+str(num_bits))
    cellarray = gdspy.CellArray(lib.cells[cellnames['bit_cell']],
                                num_bits,1,
                                cell_get_dim(lib.cells[cellnames['bit_cell']])[1],
                                cell_get_dim(lib.cells[cellnames['bit_cell']])[0])
    #add cell
    bit_arr_cell.add(cellarray)
    
    mat_arr_cell = lib.new_cell(name=mat_prefix+str(num_bits))
    matarray = gdspy.CellArray(lib.cells[cell_prefix+str(num_bits)],
                                1,num_words,
                                cell_get_dim(lib.cells[cell_prefix+str(num_bits)])[1],
                                cell_get_dim(lib.cells[cell_prefix+str(num_bits)])[0])
    #add cell
    mat_arr_cell.add(matarray)

    ########################################################
    # generate dido, mux, sense amp
    ########################################################

    #generate dido array
    dido_arr_cell = lib.new_cell(name=pchg_prefix+str(num_bits))
    didoarray = gdspy.CellArray(lib.cells[cellnames['dido']],
                            num_bits,1,
                            cell_get_dim(lib.cells[cellnames['dido']])[1],
                            cell_get_dim(lib.cells[cellnames['dido']])[0])
    dido_arr_cell.add(didoarray)

    # #generate sense amplifier array
    # se_arr_cell = lib.new_cell(name=amp_prefix+str(mem_bits))
    # searray = gdspy.CellArray(lib.cells[cellnames['sense_amplifier']],
    #                         mem_bits,1,
    #                         [col_mux*lib.cells[cellnames['dido']].get_bounding_box()[1][0],
    #                         lib.cells[cellnames['sense_amplifier']].get_bounding_box()[1][1]],
    #                         [0,0])
    # se_arr_cell.add(searray)

    #create horzontal lines M2
    #get positions of all inputs
    layer = "M2_pin"
    l_num = layers[layer][0]

    Y_dido = 0
    Xs_dido = []
    for l in dido_arr_cell.get_labels():
        if re.search("^SEL$|^DR$|^DR_$|^DW$|^DW_$",l.text) and l.layer == l_num:
            Y_dido = l.position[1]
            Xs_dido.append(l.position[0])
    Xs_dido.sort()
    #line from first occurance to last occurance
    pin_order = [0, 1, 2, 3, 4]
    Xs_dido_split  = split_lists = [Xs_dido[x:x+col_mux*len(pin_order)] for x in range(0, len(Xs_dido), col_mux*len(pin_order))]
    Xs_dido_chunks = [Xs_dido[i:i + len(pin_order)] for i in range(0, len(Xs_dido), len(pin_order))] 
    #sel, clk, saen need to go all the way
    sel_pin = 2
    p = pin_order[sel_pin]
    p_last = p - len(pin_order)

    mux_arr = lib.new_cell(name="mux_arr"+str(col_mux))
    #generate horizontal wires
    # layer = "M2_drw"
    # via = "VIA2_drw"
    # l_w = rules[layer][0]
    # v_w = rules[via][0]
    # v_encl = rules[via][1]
    # l_s = rules[layer][1]
    # ltol_dist = l_w/2 + v_encl/2 + l_s

    # l_num = layers[layer][0]
    # l_data = layers[layer][1]

    layer = "M3_drw"
    l_w = rules[layer][0]
    l_s = rules[layer][1]
    l_num = layers[layer][0]
    l_data = layers[layer][1]

    v1_w        = rules["VIA2_drw"][0]
    v1_encl_t   = rules["VIA2_drw"][2][0]

    v2_w        = rules["VIA2_drw"][0]
    v2_encl_b   = rules["VIA2_drw"][1][0]
    #FIXME: here it should be via1_top to via2_bot
    ltol_dist = v1_w/2 + v1_encl_t + v2_w/2 + v2_encl_b + l_s

    sel_lines = gdspy.Path(width= l_w, initial_point=(0, 0), number_of_paths=col_mux, distance=ltol_dist)
    sel_lines.segment(Xs_dido[p_last]-0, "+x", layer=l_num,datatype=l_data)
    sel_lines_width = sel_lines.get_bounding_box()[1][1]
    sel_lines.translate(0, -1.2*sel_lines_width)
    mux_arr.add(sel_lines)

    #generate vias
    layer = "M2_drw"
    via = "VIA2_drw"
    l_w = rules[layer][0]
    v_w = rules[via][0]
    v_encl_bot = rules[via][1]
    v_encl_top = rules[via][2]
    l_s = rules[layer][1]

    l_num = layers[layer][0]
    l_data = layers[layer][1]

    v_num = layers[via][0]
    v_data = layers[via][1]

    sel_lines_Ys = []
    for p in sel_lines.polygons:
        sel_lines_Ys.append(p[0][1]-rules["M3_drw"][0]/2)
    j = 0
    for i in range(len(Xs_dido_chunks)):   
        x = Xs_dido_chunks[i][sel_pin]
        y = sel_lines_Ys[int(j%col_mux)]
        sel_lines_vert = gdspy.Path(width= l_w, initial_point=(x, Y_dido), number_of_paths=1)
        sel_lines_vert.segment(Y_dido-y, "-y", layer=l_num,datatype=l_data)
        mux_arr.add(sel_lines_vert)
        mux_arr.add(gdspy.Rectangle((x-v_w/2, y-v_w/2), (x+v_w/2, y+v_w/2), layer=v_num, datatype=v_data))
        mux_arr.add(gdspy.Rectangle((x-v_encl_bot[0]-v_w/2, y-v_encl_bot[1]-v_w/2), (x+v_encl_bot[0]+v_w/2, y+v_encl_bot[1]+v_w/2), layer=l_num, datatype=l_data))
        mux_arr.add(gdspy.Rectangle((x-v_encl_top[0]-v_w/2, y-v_encl_top[1]-v_w/2), (x+v_encl_top[0]+v_w/2, y+v_encl_top[1]+v_w/2), layer=l_num+1, datatype=l_data))
        j = j+1

    # #the rest stay within mux size
    # #get sense amplifier pins
    # layer = "M3_pin"
    # l_num = layers[layer][0]

    # Y_samp = 0
    # Xs_samp = []
    # for l in se_arr_cell.get_labels():
    #     if re.search("^clk$|^SAEN$|^DR$|^DR_$|^DW$|^DW_$",l.text) and l.layer == l_num:
    #         Y_samp = l.position[1]
    #         Xs_samp.append(l.position[0])
    # Xs_samp.sort()
    # pin_order_samp = [0,1,2,3,4,5]
    # Xs_samp_split = split_lists = [Xs_samp[x:x+len(pin_order_samp)] for x in range(0, len(Xs_samp), len(pin_order_samp))]

    # #clk and saen
    # layer = "M2_drw"
    # via = "VIA2_drw"
    # l_w = rules[layer][0]
    # v_w = rules[via][0]
    # v_encl = rules[via][1]
    # l_s = rules[layer][1]
    # ltol_dist = l_w/2 + v_encl/2 + l_s

    # l_num = layers[layer][0]
    # l_data = layers[layer][1]

    # Xs_samp_split
    # samp_lines = gdspy.Path(width= v_encl, initial_point=(0, 0), number_of_paths=2, distance=ltol_dist)
    # samp_lines.segment(Xs_samp_split[-1][1]-0, "+x", layer=l_num,datatype=l_data)
    # samp_lines_width = samp_lines.get_bounding_box()[1][1]
    # samp_lines.translate(0, sel_lines.get_bounding_box()[0][1]-samp_lines_width-l_s)
    # mux_arr.add(samp_lines)


    # i = 0
    # mux_lines_Ys = []
    # for m in Xs_dido_split:
    #     for p in pin_order[1:]:
    #         p_last = p - len(pin_order)
    #         #generate horizontal wires
    #         x = Xs_samp_split[i][p+1]-l_w/2
    #         mux_lines = gdspy.Path(width= v_encl, initial_point=(x, sel_lines.get_bounding_box()[0][1]-samp_lines_width-l_s-(p+1)*ltol_dist), number_of_paths=1)
    #         mux_lines.segment(m[p_last]+v_encl/2+l_w-x, "+x", layer=l_num,datatype=l_data)
    #         mux_arr.add(mux_lines)
    #         for q in mux_lines.polygons:
    #             mux_lines_Ys.append(q[0][1]-v_encl/2)
    #     i = i+1

    # layer = "M3_drw"
    # via = "VIA2_drw"
    # l_w = rules[layer][0]
    # v_w = rules[via][0]
    # v_encl = rules[via][1]
    # l_s = rules[layer][1]

    # l_num = layers[layer][0]
    # l_data = layers[layer][1]

    # v_num = layers[via][0]
    # v_data = layers[via][1]

    # for i in range(len(Xs_samp_split)):
    #     p = 0
    #     for q in samp_lines.polygons:
    #                 y =  q[0][1]-v_encl/2
    #                 x = Xs_samp_split[i][p]
    #                 samp_lines_vert = gdspy.Path(width= l_w, initial_point=(x,y), number_of_paths=1)
    #                 samp_lines_vert.segment(abs(mux_arr.get_bounding_box()[0][1])-abs(y), "-y", layer=l_num,datatype=l_data)
    #                 mux_arr.add(samp_lines_vert)
    #                 y = y
    #                 mux_arr.add(gdspy.Rectangle((x-v_w/2, y-v_w/2), (x+v_w/2, y+v_w/2), layer=v_num, datatype=v_data))
    #                 mux_arr.add(gdspy.Rectangle((x-v_encl/2, y-v_encl/2), (x+v_encl/2, y+v_encl/2), layer=l_num-1, datatype=l_data))
    #                 mux_arr.add(gdspy.Rectangle((x-v_encl/2, y-v_encl/2), (x+v_encl/2, y+v_encl/2), layer=l_num, datatype=l_data))
    #                 p = p+1

    # #the rest
    # layer = "M2_drw"
    # via = "VIA2_drw"
    # l_w = rules[layer][0]
    # v_w = rules[via][0]
    # v_encl = rules[via][1]
    # l_s = rules[layer][1]
    # ltol_dist = l_w/2 + v_encl/2 + l_s

    # l_num = layers[layer][0]
    # l_data = layers[layer][1]

    # i = 0
    # for m in Xs_dido_split:
    #     for p in pin_order[1:]:
    #         p_last = p - len(pin_order)
    #         #generate horizontal wires
    #         x = Xs_samp_split[i][p+1]-l_w/2
    #         mux_lines = gdspy.Path(width= v_encl, initial_point=(x, sel_lines.get_bounding_box()[0][1]-samp_lines_width-l_s-(p+1)*ltol_dist), number_of_paths=1)
    #         mux_lines.segment(m[p_last]+v_encl/2+l_w-x, "+x", layer=l_num,datatype=l_data)
    #         for q in mux_lines.polygons:
    #             amp_lines_vert = gdspy.Path(width= l_w, initial_point=(x+l_w/2, q[0][1]-l_w), number_of_paths=1)
    #             amp_lines_vert.segment(abs(mux_arr.get_bounding_box()[0][1])-abs(q[0][1]-l_w), "-y", layer=l_num+1,datatype=l_data)
    #             mux_arr.add(amp_lines_vert)
    #     i = i+1

    # #connect dido pins to lines M2-M3 vias
    # layer = "M3_drw"
    # via = "VIA2_drw"
    # l_w = rules[layer][0]
    # v_w = rules[via][0]
    # v_encl = rules[via][1]
    # l_s = rules[layer][1]

    # l_num = layers[layer][0]
    # l_data = layers[layer][1]

    # v_num = layers[via][0]
    # v_data = layers[via][1]

    # j = 0
    # for i in range(len(Xs_dido)):
    #     if i % 5:    
    #         x = Xs_dido[i]
    #         y = mux_lines_Ys[int(j%4)]
    #         mux_lines_vert = gdspy.Path(width= l_w, initial_point=(x, Y_dido), number_of_paths=1)
    #         mux_lines_vert.segment(Y_dido-y, "-y", layer=l_num,datatype=l_data)
    #         mux_arr.add(mux_lines_vert)
    #         mux_arr.add(gdspy.Rectangle((x-v_w/2, y-v_w/2), (x+v_w/2, y+v_w/2), layer=v_num, datatype=v_data))
    #         mux_arr.add(gdspy.Rectangle((x-v_encl/2, y-v_encl/2), (x+v_encl/2, y+v_encl/2), layer=l_num-1, datatype=l_data))
    #         mux_arr.add(gdspy.Rectangle((x-v_encl/2, y-v_encl/2), (x+v_encl/2, y+v_encl/2), layer=l_num, datatype=l_data))
    #         j = j+1
    # #generate clk and saen

    ########################################################
    # generate decoder
    ########################################################
    row_dec_cell = lib.new_cell(name=dec_prefix+str(num_words))

    #create 2to4 array
    num = int(row_bits/2 - 1)
    #create last: either 3to8 or 2to4
    declast = None
    num_predec_lines = num*4
    if row_bits % 2 != 0:
        dec_unit = lib.cells[cellnames['dec_3to6']]
        num_predec_lines += 6
    else:
        dec_unit = lib.cells[cellnames['dec_2to4']]
        num_predec_lines += 4
    dec_unit_width = dec_unit.get_bounding_box()[1][0]
    #######################
    # nand column
    #######################
    gate = cellnames['nand'+str(num_inputs)]
    nandarray = gdspy.CellArray(lib.cells[gate],
                                1,num_words,
                                cell_get_dim(lib.cells[gate])[1],
                                cell_get_dim(lib.cells[gate])[0])
    row_dec_cell.add(nandarray)
    #######################
    # predecoder lines
    #######################
    layer = "M2_drw"
    l_w = rules[layer][0]
    l_s = rules[layer][1]
    l_num = layers[layer][0]
    l_data = layers[layer][1]

    v1_w        = rules["VIA1_drw"][0]
    v1_encl_t   = rules["VIA1_drw"][2][0]

    v2_w        = rules["VIA2_drw"][0]
    v2_encl_b   = rules["VIA2_drw"][1][0]
    #FIXME: here it should be via1_top to via2_bot
    ltol_dist = v1_w/2 + v1_encl_t + v2_w/2 + v2_encl_b + l_s

    pre_dec_lines = gdspy.Path(width=l_w, initial_point=(0, -0.02), number_of_paths=num_predec_lines, distance=ltol_dist)#width, spacing: C-C
    pre_dec_lines.segment(nandarray.get_bounding_box()[1][1]+1, "+y", layer=l_num,datatype=l_data) #layer: M2=32, Datatype = 0
    width_pre_dec_lines = pre_dec_lines.get_bounding_box()[1][0]
    pre_dec_lines.translate(-(width_pre_dec_lines+ltol_dist),0)
    row_dec_cell.add(pre_dec_lines)

    #get positions of all inputs
    layer = "M1_pin"
    l_num = layers[layer][0]

    Ys_nand_col = []
    X_nand_col = 0
    for l in row_dec_cell.get_labels():
        if re.search("^A$|^B$|^C$|^D$",l.text) and l.layer == l_num:
            X_nand_col = l.position[0]
            Ys_nand_col.append(l.position[1])
    Ys_nand_col.sort(reverse=True)

    #######################
    # not column
    #######################
    gate = cellnames['not']
    notarray = gdspy.CellArray(lib.cells[gate],
                                1,num_words,
                                cell_get_dim(lib.cells[gate])[1],
                                cell_get_dim(lib.cells[gate])[0])
    row_dec_cell.add(notarray)
    notarray.translate(nandarray.get_bounding_box()[1][0],0)

    #######################
    # decoder column
    #######################
    declast = gdspy.CellReference(dec_unit,[-(2*width_pre_dec_lines+2*ltol_dist+dec_unit_width),0]) 
    row_dec_cell.add(declast)
    if(num != 0):
        decarray = gdspy.CellArray(lib.cells[cellnames['dec_2to4']],
                                1,num,
                                cell_get_dim(lib.cells[cellnames['dec_2to4']])[1],
                                [-(2*width_pre_dec_lines+2*ltol_dist+dec_unit_width),
                                dec_unit.get_bounding_box()[1][1]])
        row_dec_cell.add(decarray)

    Ys = []
    X = 0
    #get all ys of labels
    layer = "M3_pin"
    l_num = layers[layer][0]

    for l in row_dec_cell.get_labels():
        if re.search("^Y[\d]+$",l.text) and l.layer == l_num:
            X = l.position[0]
            Ys.append(l.position[1])
    #sort them from biggest to smallest
    Ys = list(set(Ys))
    Ys.sort(reverse=True)

    #######################
    # decoder to vertical
    #######################
    layer = "M3_drw"
    via = "VIA2_drw"
    l_w = rules[layer][0]
    v_w = rules[via][0]
    v_encl_bot = rules[via][1]
    v_encl_top = rules[via][2]
    l_s = rules[layer][1]

    l_num = layers[layer][0]
    l_data = layers[layer][1]

    v_num = layers[via][0]
    v_data = layers[via][1]

    pre_dec_lines_Xs = []
    for p in pre_dec_lines.polygons:
        pre_dec_lines_Xs.append(p[0][0]+rules["M2_drw"][0]/2)
        
    for i in range(len(Ys)):
        #generate horizontal wires
        in_dec_lines = gdspy.Path(width= l_w, initial_point=(X, Ys[i]), number_of_paths=1)
        in_dec_lines.segment(pre_dec_lines_Xs[i]-X, "+x", layer=l_num,datatype=l_data)
        #generate vias
        x = pre_dec_lines_Xs[i]
        y = Ys[i]
        row_dec_cell.add(gdspy.Rectangle((x-v_w/2, y-v_w/2), (x+v_w/2, y+v_w/2), layer=v_num, datatype=v_data))
        row_dec_cell.add(gdspy.Rectangle((x-v_encl_bot[0]-v_w/2, y-v_encl_bot[1]-v_w/2), (x+v_encl_bot[0]+v_w/2, y+v_encl_bot[1]+v_w/2), layer=l_num-1, datatype=l_data))
        row_dec_cell.add(gdspy.Rectangle((x-v_encl_top[0]-v_w/2, y-v_encl_top[1]-v_w/2), (x+v_encl_top[0]+v_w/2, y+v_encl_top[1]+v_w/2), layer=l_num, datatype=l_data))
        row_dec_cell.add(in_dec_lines)

    #######################
    # nand to vertical
    #######################
    layer = "M1_drw"
    via = "VIA1_drw"
    l_w = rules[layer][0]
    v_w = rules[via][0]
    v_encl_bot = rules[via][1]
    v_encl_top = rules[via][2]
    l_s = rules[layer][1]

    l_num = layers[layer][0]
    l_data = layers[layer][1]

    v_num = layers[via][0]
    v_data = layers[via][1]

    for i in range(num_words):
        for j in range(num_inputs):
            l_idx = (4*j + int((i/pow(4,j))%4))
            #generate horizontal wires
            in_dec_lines = gdspy.Path(width= l_w, initial_point=(X_nand_col, Ys_nand_col[num_inputs*i+j]), number_of_paths=1)
            in_dec_lines.segment(X_nand_col-pre_dec_lines_Xs[l_idx], "-x", layer=l_num,datatype=l_data)
            #generate vias
            x = pre_dec_lines_Xs[l_idx]
            y = Ys_nand_col[num_inputs*i+j]
            row_dec_cell.add(gdspy.Rectangle((x-v_w/2, y-v_w/2), (x+v_w/2, y+v_w/2), layer=v_num, datatype=v_data))
            row_dec_cell.add(gdspy.Rectangle((x-v_encl_bot[0]-v_w/2, y-v_encl_bot[1]-v_w/2), (x+v_encl_bot[0]+v_w/2, y+v_encl_bot[1]+v_w/2), layer=l_num, datatype=l_data))
            row_dec_cell.add(gdspy.Rectangle((x-v_encl_top[0]-v_w/2, y-v_encl_top[1]-v_w/2), (x+v_encl_top[0]+v_w/2, y+v_encl_top[1]+v_w/2), layer=l_num+1, datatype=l_data))
            row_dec_cell.add(in_dec_lines)

    # #######################
    # # row driver
    # #######################
    row_driver_arr_cell = lib.new_cell(name='row_driver'+str(mem_bits))
    row_driver_array = gdspy.CellArray(lib.cells[cellnames['row_driver']],
                            1,num_words,
                            cell_get_dim(lib.cells[cellnames['row_driver']])[1],
                            cell_get_dim(lib.cells[cellnames['row_driver']])[0])
    row_driver_arr_cell.add(row_driver_array)

    #######################
    # input reg col
    #######################

    layer = "M1_pin"
    l_num = layers[layer][0]
    l_w = rules["M1_drw"][0]
    Ys = []
    X = 0
    #get all As of labels
    for l in row_dec_cell.get_labels():
        if re.search("^A[\d]+$",l.text) and l.layer == l_num:
            X = l.position[0]
            Ys.append(l.position[1])
    #sort them from biggest to smallest
    Ys = list(set(Ys))
    Ys.sort(reverse=True)

    addr_reg_cell = lib.new_cell(name="addr_reg")
    gate = cellnames['in_reg']

    # get d position
    for l in lib.cells[gate].get_labels():
        if re.search("^q$",l.text) and l.layer == l_num:
            Y_q = l.position[1]

    for i in range(int(row_bits)):
        reg_cell = gdspy.CellReference(lib.cells[gate],  [X-cell_get_dim(lib.cells[gate])[1][0]-l_w/2,Ys[i]-Y_q])
        addr_reg_cell.add(reg_cell)

    ########################################################################
    # col decoder

    ########################################################################
    #control
    # ctrl_cell = lib.new_cell(name="ctrl_cell")
    # ctrl_cell.add(lib.cells[cellnames['control']])

    # del_arr_cell = lib.new_cell(name="del_arr_cell")
    # delarray = gdspy.CellArray(lib.cells[cellnames['del_cell']],
    #                             delay_val,1,
    #                             [lib.cells[cellnames['del_cell']].get_bounding_box()[1][0],
    #                             lib.cells[cellnames['del_cell']].get_bounding_box()[1][1]],
    #                             [0,
    #                             0])
    # del_arr_cell.add(delarray)
    # # get delay_pins
    # Ys = []
    # X = 0
    # #get all As of labels
    # for l in ctrl_cell.get_labels():
    #     if re.search("^del|^PCHG$",l.text) and l.layer == 131:
    #         X = l.position[0]
    #         Ys.append(l.position[1])
    # #sort them from biggest to smallest
    # Ys = list(set(Ys))
    # Ys.sort(reverse=True)

    # del1 = gdspy.CellReference(del_arr_cell,  [X+0.04,Ys[0]-0.885])
    # del2 = gdspy.CellReference(del_arr_cell,  [X+0.04,Ys[1]-0.885])
    # del3 = gdspy.CellReference(del_arr_cell,  [X+0.04,Ys[2]-0.885])
    # del4 = gdspy.CellReference(del_arr_cell,  [X+0.04,Ys[3]-0.885])

    # ctrl_cell.add(del1)
    # ctrl_cell.add(del2)
    # ctrl_cell.add(del3)
    # ctrl_cell.add(del4)

    #merge
    #matrix
    cell.add(gdspy.CellReference(mat_arr_cell,  [0,0]))
    #row_decoder
    cell.add(gdspy.CellReference(row_dec_cell,  [-(row_dec_cell.get_bounding_box()[1][0]+row_driver_arr_cell.get_bounding_box()[1][0]),0]))#WL label position
    #row driver
    cell.add(gdspy.CellReference(row_driver_arr_cell,  [-(row_driver_arr_cell.get_bounding_box()[1][0]),0]))
    # address reg
    cell.add(gdspy.CellReference(addr_reg_cell,  [-(row_dec_cell.get_bounding_box()[1][0]+row_driver_arr_cell.get_bounding_box()[1][0]),0]))
    # #col decoder
    # cell.add(gdspy.CellReference(lib.cells["cd"+str(col_mux)+"col_dec"+str(col_mux)],  [-lib.cells["cd"+str(col_mux)+"col_dec"+str(col_mux)].get_bounding_box()[1][0],-lib.cells["cd"+str(col_mux)+"col_dec"+str(col_mux)].get_bounding_box()[1][1]]))
    # #control
    # cell.add(gdspy.CellReference(ctrl_cell,  [-ctrl_cell.get_bounding_box()[1][0]-0.495,-ctrl_cell.get_bounding_box()[1][1]-lib.cells["cd"+str(col_mux)+"col_dec"+str(col_mux)].get_bounding_box()[1][1]]))
    #dido
    cell.add(gdspy.CellReference(dido_arr_cell, [0,-dido_arr_cell.get_bounding_box()[1][1]]))
    #mux_arr
    cell.add(gdspy.CellReference(mux_arr, [0,-dido_arr_cell.get_bounding_box()[1][1]]))
    # #sense amplifier
    # cell.add(gdspy.CellReference(se_arr_cell,   [0,mux_arr.get_bounding_box()[0][1]-(dido_arr_cell.get_bounding_box()[1][1] + se_arr_cell.get_bounding_box()[1][1])]))
    #write gds
    print("Writing out GDS file -> "+"out/"+top_name+'.gds')
    lib.write_gds("out/"+top_name+'.gds')
