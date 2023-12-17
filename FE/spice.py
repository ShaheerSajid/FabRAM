##############################################################
# Imports
##############################################################
import math
import re
import time
import sys
import PySpice.Logging.Logging as Logging
import pkg_resources
logger = Logging.setup_logging()
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Parser import SpiceParser
from PySpice.Unit import *


#array names
cell_prefix     = "bit_arr_"
dmycell_prefix  = "dmy_arr_"
mat_prefix      = "mat_arr_"
amp_prefix      = "se_arr_"
pchg_prefix     = "pchg_arr_"
dec_prefix      = "dec_arr_"
col_dec_prefix  = "cdec_arr_"
dido_prefix     = "dido_arr_"
rd_prefix       = "rd_arr_"

# bit cell row generation
def dmy_array_gen(words, dmy_cell_name):
    nodes = 'VDD VSS'
    for i in range(words):
        nodes += ' WL'+str(i)
    nodes += ' DBL DBL_'
    circuit = SubCircuit(dmycell_prefix+str(words), nodes)
    for i in range(words):
        circuit.X(str(i), dmy_cell_name,'VDD','VSS','WL'+str(i),'DBL','DBL_')
    return circuit


# bit cell row generation
def sram_array_gen(len, bit_cell_name):
    subckt = 'VDD VSS'
    for i in range(len):
        subckt += ' BL'+str(i)+' BL_'+str(i)
    subckt += ' WL'
    circuit = SubCircuit(cell_prefix+str(len), subckt)
    for i in range(len):
        circuit.X(str(i), bit_cell_name, 'VDD', 'VSS', 'WL', 'BL'+str(i), 'BL_'+str(i))
    return circuit

# sense amplifier array generation
def se_array_gen(len, sense_amp_name):
    subckt = 'VDD VSS SAEN'
    for i in range(len):
        subckt += ' BL'+str(i)+' BL_'+str(i) 
    for i in range(len):
        subckt += ' SB'+str(i)
    circuit = SubCircuit(amp_prefix+str(len), subckt)
    for i in range(len):
        circuit.X(str(i), sense_amp_name, 'VDD', 'VSS', 'SAEN', 'BL'+str(i), 'BL_'+str(i), 'SB'+str(i))
    return circuit

# bit cell replicate rows
def mat_array_gen(words, size, sram_row_array_name):
    nodes = 'VDD VSS'
    for i in range(size):
        nodes += ' BL'+str(i)+' BL_'+str(i)
    nodes_cp = nodes
    for i in range(words):
        nodes += ' WL'+str(i)
    circuit = SubCircuit(mat_prefix+str(size), nodes)
    for i in range(words):
        circuit.X(str(i), sram_row_array_name, nodes_cp, 'WL'+str(i))
    return circuit

# master slave flip flop array
def input_block_gen(name, inputs,ms_reg_name):
    nodes = 'VDD VSS clk'
    for i in range(inputs):
        nodes += ' D'+str(i)
    for i in range(inputs):
        nodes += ' Q'+str(i)
    #nodes += ' VSS'
    circuit = SubCircuit(name+str(inputs), nodes)
    for i in range(inputs):
        circuit.X(str(i), ms_reg_name, 'VDD','VSS','clk', 'D'+str(i), 'Q'+str(i))
    return circuit

# digital in digital out array
def dido_array_gen(len, dido_name):
    subckt = 'VDD VSS PCHG WREN'
    for i in range(len):
        subckt += ' SEL'+str(i)
    for i in range(len):
        subckt += ' BL'+str(i)+' BL_'+str(i) 
    for i in range(len):
        subckt += ' DW'+str(i)+' DW_'+str(i) 
    for i in range(len):
        subckt += ' DR'+str(i)+' DR_'+str(i) 
    circuit = SubCircuit(dido_prefix+str(len), subckt)
    for i in range(len):
        circuit.X(str(i),  dido_name, 'VDD','VSS', 'PCHG', 'WREN', 'SEL'+str(i),'BL'+str(i), 'BL_'+str(i),'DW'+str(i), 'DW_'+str(i),'DR'+str(i), 'DR_'+str(i))
    return circuit

# write driver array gneration
def data_write_arr_gen(name, len, ms_reg_name):
    subckt = 'VDD VSS clk'
    for i in range(len):
        subckt += ' din'+str(i)
    for i in range(len):
        subckt += ' DW'+str(i)+' DW_'+str(i) 
    circuit = SubCircuit(name+str(len), subckt)
    for i in range(len):
        circuit.X(str(i), ms_reg_name, 'VDD','VSS', 'clk', 'din'+str(i), 'din_r'+str(i))
    for i in range(len):
        # circuit.M(str(4*i  ),'DW_'+str(i),'din_r'+str(i),'VDD' ,'VDD',model=blocks.pmos_device,l='150n',w='4u')
        # circuit.M(str(4*i+1),'DW_'+str(i),'din_r'+str(i),'VSS' ,'VSS',model=blocks.nmos_device,l='150n',w='4u')
        # circuit.M(str(4*i+2),'DW'+str(i),   'DW_'+str(i),'VDD' ,'VDD',model=blocks.pmos_device,l='150n',w='4u')
        # circuit.M(str(4*i+3),'DW'+str(i),   'DW_'+str(i),'VSS' ,'VSS',model=blocks.nmos_device,l='150n',w='4u')
        circuit.X(str(4*i  +len),blocks.pmos_device,'DW_'+str(i),'din_r'+str(i),'VDD' ,'VDD',l='0.15',w='4')
        circuit.X(str(4*i+1+len),blocks.nmos_device,'DW_'+str(i),'din_r'+str(i),'VSS' ,'VSS',l='0.15',w='4')
        circuit.X(str(4*i+2+len),blocks.pmos_device,'DW'+str(i),   'DW_'+str(i),'VDD' ,'VDD',l='0.15',w='4')
        circuit.X(str(4*i+3+len),blocks.nmos_device,'DW'+str(i),   'DW_'+str(i),'VSS' ,'VSS',l='0.15',w='4')
    return circuit

# row driver array generation
def row_driver_arr(num_words,cell_name):
    subckt = 'VDD VSS WLEN'
    for i in range(num_words):
        subckt += ' DC'+str(i)
    for i in range(num_words):
        subckt += ' WL'+str(i)
    circuit = SubCircuit(rd_prefix+str(num_words), subckt)
    for i in range(num_words):
        circuit.X(str(i),cell_name,'VDD','VSS','WLEN','DC'+str(i),'WL'+str(i))
    return circuit


#fix: move to primitives section
# 2 to 4 decoder
def dec_2to4(name, not_name, nand2_name):
    circuit = SubCircuit(name, 'VDD VSS A1 A0 Y0 Y1 Y2 Y3')
    circuit.X(0, not_name, 'VDD VSS A1 A_1')
    circuit.X(1, not_name, 'VDD VSS A0 A_0')
    circuit.X(2, nand2_name, 'VDD VSS A_1 A_0 Y0_')
    circuit.X(3, nand2_name, 'VDD VSS A_1 A0 Y1_')
    circuit.X(4, nand2_name, 'VDD VSS A1 A_0 Y2_')
    circuit.X(5, nand2_name, 'VDD VSS A1 A0 Y3_')
    circuit.X(6, not_name, 'VDD VSS Y0_ Y0')
    circuit.X(7, not_name, 'VDD VSS Y1_ Y1')
    circuit.X(8, not_name, 'VDD VSS Y2_ Y2')
    circuit.X(9, not_name, 'VDD VSS Y3_ Y3')
    return circuit

# 3 to 6 decoder
def dec_3to6(name, dec_2to4_name, not_name):
    circuit = SubCircuit(name, 'VDD VSS A2 A1 A0 Y0 Y1 Y2 Y3 Y4 Y5')
    circuit.X(0, not_name, 'VDD VSS A2 Y4')
    circuit.X(1, not_name, 'VDD VSS Y4 Y5')
    circuit.X(2, dec_2to4_name, 'VDD VSS A1 A0 Y0 Y1 Y2 Y3')
    return circuit

# nand decoder
def nand_dec(name, num_words, not_name, dec2to4_name, dec3to6_name, is_col):
    addr_bits = math.log2(num_words)
    subckt = ''
    for i in range(math.ceil((addr_bits))):
        subckt += ' A'+str(i)
    for i in range(num_words):
        subckt += ' DC'+str(i)
    r_dec = SubCircuit(name+str(num_words), 'VDD VSS' + subckt)

    Xcnt = 0
    for i in range(int(addr_bits/2 - 1)):
        r_dec.X(str(i), 
                dec2to4_name, 
                'VDD',
                'VSS',
                'A'+str(2*i+1), 
                'A'+str(2*i), 
                'Y'+str(4*i),
                'Y'+str(4*i+1),
                'Y'+str(4*i+2),
                'Y'+str(4*i+3)
                )
        Xcnt = i + 1
    
    if addr_bits % 2 != 0:
        r_dec.X(str(Xcnt), 
                dec3to6_name, 
                'VDD',
                'VSS',
                'A'+str(2*Xcnt+2),
                'A'+str(2*Xcnt+1) ,
                'A'+str(2*Xcnt), 
                'Y'+str(4*Xcnt),
                'Y'+str(4*Xcnt+1),
                'Y'+str(4*Xcnt+2),
                'Y'+str(4*Xcnt+3),
                'Y'+str(4*Xcnt+4),
                'Y'+str(4*Xcnt+5)
                )
    else:
        r_dec.X(str(Xcnt), 
                dec2to4_name, 
                'VDD',
                'VSS',
                'A'+str(2*Xcnt+1), 
                'A'+str(2*Xcnt), 
                'Y'+str(4*Xcnt),
                'Y'+str(4*Xcnt+1),
                'Y'+str(4*Xcnt+2),
                'Y'+str(4*Xcnt+3)
                )
    #generate nand-not column
    #check how many input nand is needed
    if addr_bits > 2:
        num_inputs = math.ceil(math.log(num_words, 4))
        for i in range(num_words):
            gate = 'nand'+str(num_inputs)
            in_ports = ""
            for j in range(num_inputs):
                in_ports += ' Y'+str(4*j + int((i/pow(4,j))%4))
            r_dec.X(str(Xcnt+1+i), 
                    gate, 
                    'VDD'+
                    ' VSS'+
                    in_ports +
                    ' DC_'+str(i)
                    )
    #invert output
        if not is_col:
            for i in range(num_words):
                r_dec.X(str(Xcnt+1+i+num_words),
                        not_name,
                        'VDD'+
                        ' VSS'+
                        ' DC_'+str(i)+
                        ' DC'+str(i)
                        )
    else:
        for i in range(num_words):
            r_dec.X(str(Xcnt+1+i),
                    not_name,
                    'VDD'+
                    ' VSS'+
                    ' Y'+str(i)+
                    ' DC'+str(i)
                    )
    return r_dec

# delay cell
def del_cell(name, delay, not_name, notdel_name, nand2_name):
    pos_pulse_detector = SubCircuit(name+str(delay), 'VDD VSS A B')
    pos_pulse_detector.X(0, notdel_name, 'VDD', 'VSS', 'A'  , 'net1')
    for i in range(delay):
        pos_pulse_detector.X(i+1, notdel_name, 'VDD', 'VSS', 'net'+str(i+1), 'net'+str(i+2))
    pos_pulse_detector.X(delay+1, nand2_name, 'VDD', 'VSS', 'A', 'net'+str(delay+1), 'net'+str(delay+2))
    pos_pulse_detector.X(delay+2, not_name, 'VDD', 'VSS', 'net'+str(delay+2), 'B')
    return pos_pulse_detector
##############################################################
# Generate SPICE
##############################################################
import blocks

def gen_spice(mem_words, mem_bits, col_mux):
    #rows
    num_words = int(mem_words/col_mux)
    #columns
    num_bits = mem_bits*col_mux
    top_name        = 'sram'+str(mem_words)+'x'+str(mem_bits)
    #top level name
    circuit = Circuit("sram_gen")
    #bit cell
    bit_Cell    = blocks.bit_cell_gen('bit_cell')
    #dmy cell
    dmy_Cell    = blocks.dmy_cell_gen('dmy_cell')
    #in_reg cell
    in_reg      = blocks.ms_reg_gen('in_reg')
    #se cell
    se_cell     = blocks.sense_amp_gen('se_cell')

    circuit.subcircuit(bit_Cell)
    circuit.subcircuit(dmy_Cell)
    circuit.subcircuit(in_reg)
    circuit.subcircuit(se_cell)

    #sram_arr cell
    sram_arr    = sram_array_gen(num_bits, bit_Cell.name)
    #dmy_arr cell
    dmy_arr     = dmy_array_gen(num_words, dmy_Cell.name)
    #sram_arr cell
    se_arr      = se_array_gen(mem_bits, se_cell.name)
    #mat_arr cell
    mat_arr     = mat_array_gen(num_words,num_bits, sram_arr.name)

    # create gates for decoder
    W_nand = blocks.W_nand
    L_nand = blocks.L_nand
    W_not  = blocks.W_not
    L_not  = blocks.L_not
    ratio  = blocks.ratio

    W_del       = blocks.W_del
    L_del       = blocks.L_del
    ratio_del   = blocks.ratio_del

    #primitives
    not_g       = blocks.notg("",   W_not, L_not, ratio)
    not_del_g   = blocks.notg("del",W_del, L_del, ratio_del)
    nand2_g     = blocks.nand2("",  W_nand,L_nand, ratio)
    nand3_g     = blocks.nand3("",  W_nand,L_nand, ratio)
    nand4_g     = blocks.nand4("",  W_nand,L_nand, ratio)

    circuit.subcircuit(not_g)
    circuit.subcircuit(not_del_g)
    circuit.subcircuit(nand2_g)
    circuit.subcircuit(nand3_g)
    circuit.subcircuit(nand4_g)

    addr_bits   = math.log2(mem_words)
    row_bits    = math.log2(num_words)
    col_bits    = math.log2(col_mux)
    num_inputs  = math.ceil(math.log(num_words, 4))

    #create 2to4 decoder
    dec_unit2to4    = dec_2to4("dec_2to4", not_g.name, nand2_g.name)
    dec_unit3to6    = dec_3to6("dec_3to6", dec_unit2to4.name, not_g.name)
    circuit.subcircuit(dec_unit2to4)
    circuit.subcircuit(dec_unit3to6)
    r_dec           = nand_dec('row_dec', num_words, not_g.name, dec_unit2to4.name, dec_unit3to6.name, is_col = 0)

    circuit.subcircuit(r_dec)

    #row_driver cell
    row_driver_cell = blocks.row_driver_cell('row_driver',nand2_g.name)
    circuit.subcircuit(row_driver_cell)
    row_driver      = row_driver_arr(num_words,row_driver_cell.name)
    circuit.subcircuit(row_driver)

    #create col decoder
    c_dec   = nand_dec('col_dec', col_mux, not_g.name, dec_unit2to4.name, dec_unit3to6.name,  is_col = 1)
    circuit.subcircuit(c_dec)
    #dido block (prc, read/write logic)
    dido    = blocks.dido_gen("dido",not_g.name,nand2_g.name)
    circuit.subcircuit(dido)
    #create array
    dido_arr  = dido_array_gen(num_bits, dido.name)
    circuit.subcircuit(dido_arr)
    delay_val = 4
    input_reg_arr   = input_block_gen('input_reg', math.ceil((addr_bits)) + 1,in_reg.name)
    # din reg
    datain_reg_arr  = data_write_arr_gen('datain_reg', mem_bits, in_reg.name)
    #ctrl circuit
    pos_pulse_detector  = del_cell('del',delay_val, not_g.name, not_del_g.name, nand2_g.name)
    circuit.subcircuit(pos_pulse_detector)
    ctrl                = blocks.self_timed_ctrl("ctrl",pos_pulse_detector.name, not_g.name,nand2_g.name,nand3_g.name)
    circuit.subcircuit(ctrl)

    #assemble all together
    #generate address port list
    addr_ports = ''
    for i in range(math.ceil((addr_bits))):
        addr_ports += ' addr'+str(i) 
    a_ports = ''
    for i in range(math.ceil((addr_bits))):
        a_ports += ' A'+str(i) 
    #generate din ports
    din_ports = ''
    for i in range(mem_bits):
        din_ports += ' din'+str(i)
    #generate dataout port list
    dout_ports = ''
    for i in range(mem_bits):
        dout_ports += ' Q'+str(i)
        
    mem_gen = SubCircuit(top_name, 'VDD', 'VSS', 'clk' + addr_ports + din_ports + dout_ports, 'write', 'cs')
    #input block
    mem_gen.X(0, input_reg_arr.name, 'VDD','VSS', 'clk' + addr_ports + ' write' + a_ports, 'WREN')
    #add row decoder
    a_ports = ''
    for i in range(math.ceil((row_bits))):
        a_ports += ' A'+str(i+math.ceil((col_bits)))
    dc_ports = ''
    for i in range(math.ceil((num_words))):
        dc_ports += ' DC'+str(i) 
    mem_gen.X(1, r_dec.name, 'VDD', 'VSS' + a_ports + dc_ports )
    #add row driver
    mem_gen.X(2, row_driver.name, row_driver.external_nodes[0])
    #add col decoder
    a_ports = ''
    for i in range(math.ceil((col_bits))):
        a_ports += ' A'+str(i) 
    sel_lines = ''
    for i in range(col_mux):
        sel_lines += ' SEL'+str(i) 
    mem_gen.X(3, c_dec.name, 'VDD VSS'+a_ports+sel_lines)
    #add dido array
    sel_lines = ''
    for i in range(num_bits):
        sel_lines += ' SEL'+str(int(i%col_mux)) 
    for i in range(num_bits):
        sel_lines += ' BL'+str(i)+' BL_'+str(i) 
    for i in range(num_bits):
        sel_lines += ' DW'+str(int(i/col_mux))+' DW_'+str(int(i/col_mux)) 
    for i in range(num_bits):
        sel_lines += ' DR'+str(int(i/col_mux))+' DR_'+str(int(i/col_mux)) 
    mem_gen.X(4, dido_arr.name, 'VDD', 'VSS', 'PCHG', 'WREN' + sel_lines)
    #add colmux
    #add datain reg
    mem_gen.X(5, datain_reg_arr.name, datain_reg_arr.external_nodes[0])
    #add bit cell matrix
    mem_gen.X(6, mat_arr.name, mat_arr.external_nodes[0])
    #add amp array ToDo
    sb_lines = ''
    for i in range(mem_bits):
        sb_lines += ' DR'+str(i)+' DR_'+str(i) 
    for i in range(mem_bits):
        sb_lines += ' Q'+str(i)
    mem_gen.X(7, se_arr.name, 'VDD', 'VSS', 'SAEN' + sb_lines)
    #ctrl
    mem_gen.X(8, ctrl.name, ctrl.external_nodes[0])

    mem_gen.X(9, dmy_arr.name, dmy_arr.external_nodes[0])

    #linking
    circuit.subcircuit(input_reg_arr)
    circuit.subcircuit(datain_reg_arr)
    circuit.subcircuit(r_dec)
    circuit.subcircuit(sram_arr)
    circuit.subcircuit(dmy_arr)
    circuit.subcircuit(se_arr)
    circuit.subcircuit(mat_arr)
    circuit.subcircuit(ctrl)
    circuit.subcircuit(mem_gen)

    print("Writing out SPICE file -> "+"out/"+top_name+".spi")

    f = open("out/"+top_name+".spi", "w")
    f.write(str(circuit))
    f.close()

