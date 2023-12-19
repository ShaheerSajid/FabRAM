import PySpice.Logging.Logging as Logging
import pkg_resources
logger = Logging.setup_logging()
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Parser import SpiceParser
from PySpice.Unit import *

#active high wren
#active low precharge
#active high sense enable
#active high wl
#active low col select

nmos_device     = "sky130_fd_pr__nfet_01v8"
pmos_device     = "sky130_fd_pr__pfet_01v8"

W_nand = 0.42
L_nand = 0.15
W_not  = 0.42
L_not  = 0.15
ratio  = 1.0

W_del       = 0.42
L_del       = 0.15
ratio_del   = 2.0
##############################################################
# Primitives
##############################################################
# not gate
def notg(name, W,L, ratio):
    circuit = SubCircuit('not'+name, 'VDD VSS A B')
    circuit.X(0, pmos_device,'B', 'A', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(1, nmos_device,'B', 'A', 'VSS', 'VSS', w=W, l=L)
    return circuit

# 2 input nand
def nand2(name, W,L, ratio):
    circuit = SubCircuit('nand2'+name, 'VDD VSS A B Y')
    circuit.X(0, pmos_device,'Y', 'A', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(1, pmos_device,'Y', 'B', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(2, nmos_device,'Y', 'B', 'net1', 'VSS',  w=W, l=L)
    circuit.X(3, nmos_device,'net1', 'A', 'VSS', 'VSS',  w=W, l=L)
    return circuit

# 3 input nand
def nand3(name, W,L, ratio):
    circuit = SubCircuit('nand3'+name, 'VDD VSS A B C Y')
    circuit.X(0, pmos_device,'Y', 'A', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(1, pmos_device,'Y', 'B', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(2, pmos_device,'Y', 'C', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(3, nmos_device,'Y', 'A', 'net1', 'VSS',  w=W, l=L)
    circuit.X(4, nmos_device,'net1', 'B', 'net2', 'VSS',  w=W, l=L)
    circuit.X(5, nmos_device,'net2', 'C', 'VSS', 'VSS',  w=W, l=L)
    return circuit

# 4 input nand
def nand4(name, W,L, ratio):
    circuit = SubCircuit('nand4'+name, 'VDD VSS A B C Y')
    circuit.X(0, pmos_device,'Y', 'A', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(1, pmos_device,'Y', 'B', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(2, pmos_device,'Y', 'C', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(3, pmos_device,'Y', 'D', 'VDD', 'VDD',  w=ratio*W, l=L)
    circuit.X(4, nmos_device,'Y', 'D', 'net1', 'VSS',  w=W, l=L)
    circuit.X(5, nmos_device,'net1', 'B', 'net2', 'VSS',  w=W, l=L)
    circuit.X(6, nmos_device,'net2', 'C', 'net3', 'VSS',  w=W, l=L)
    circuit.X(7, nmos_device,'net3', 'A', 'VSS', 'VSS',  w=W, l=L)
    return circuit

##############################################################
# Memory Bricks
##############################################################
# Bit cell
def bit_cell_gen(name):
    circuit = SubCircuit(name, 'VDD VSS WL BL BL_')
    circuit.X(0,nmos_device, 'Q','Q_','VSS','VSS',   w='0.80',l='0.15')
    circuit.X(1,nmos_device, 'Q_','Q','VSS','VSS',   w='0.80',l='0.15')
    circuit.X(2,pmos_device,'Q','Q_','VDD','VDD',    w='0.42',l='0.15')
    circuit.X(3,pmos_device,'Q_','Q','VDD','VDD',   w='0.42',l='0.15')
    circuit.X(4,nmos_device,'Q','WL','BL' ,'VSS',    w='0.60',l='0.15')
    circuit.X(5,nmos_device,'Q_','WL','BL_','VSS',   w='0.60',l='0.15')
    return circuit

def dmy_cell_gen(name):
    circuit = SubCircuit(name, 'VDD VSS WL BL BL_')
    circuit.X(0,nmos_device, 'Q','VSS','VSS','VSS',   w='0.80',l='0.15')
    circuit.X(1,nmos_device, 'Q_','VDD','VSS','VSS',   w='0.80',l='0.15')
    circuit.X(2,pmos_device,'Q','VSS','VDD','VDD',    w='0.42',l='0.15')
    circuit.X(3,pmos_device,'Q_','VDD','VDD','VDD',   w='0.42',l='0.15')
    circuit.X(4,nmos_device,'Q','WL','BL' ,'VSS',    w='0.60',l='0.15')
    circuit.X(5,nmos_device,'Q_','WL','BL_','VSS',   w='0.60',l='0.15')
    return circuit

# sense amplifier
def sense_amp_gen(name):
    circuit = SubCircuit(name, 'VDD VSS SAEN BL BL_ SB')
    circuit.X(0,nmos_device,'net1' ,'SAEN' ,'VSS' ,'VSS' ,    w='0.84', l='0.15')
    circuit.X(1,nmos_device,'diff1','BL_'  ,'net1','net1',    w='0.42', l='0.15')
    circuit.X(2,nmos_device,'diff2','BL'   ,'net1','net1',    w='0.42', l='0.15')
    circuit.X(3,pmos_device,'diff1','diff1','VDD' ,'VDD' ,    w='0.42', l='0.15')
    circuit.X(4,pmos_device, 'diff2','diff1','VDD' ,'VDD' ,   w='0.42', l='0.15')
    circuit.X(5,pmos_device,'diff2_','diff2','VDD' ,'VDD' ,   w='2', l='0.15')
    circuit.X(6,nmos_device,'diff2_','diff2','VSS' ,'VSS' ,   w='2', l='0.15')
    circuit.X(7,pmos_device,'SB_'   ,'diff2_','VDD' ,'VDD' ,  w='2', l='0.15')
    circuit.X(8,nmos_device,'SB_'   ,'diff2_','VSS' ,'VSS' ,  w='2', l='0.15')

    circuit.X(9, nmos_device,'SB_w','Q_','VSS','VSS',         w='0.80',l='0.15')
    circuit.X(10,nmos_device, 'Q_','SB_w','VSS','VSS',        w='0.80',l='0.15')
    circuit.X(11,pmos_device, 'SB_w','Q_','VDD','VDD',        w='0.42',l='0.15')
    circuit.X(12,pmos_device, 'Q_','SB_w','VDD','VDD',        w='0.42',l='0.15')
    circuit.X(13,nmos_device, 'SB_w','SAEN','SB_' ,'VSS',     w='0.60',l='0.15')
    circuit.X(14,nmos_device, 'Q_','SAEN','diff2_','VSS',     w='0.60',l='0.15')

    circuit.X(15,pmos_device,'SB','SB_w','VDD' ,'VDD' , w='2', l='0.15')
    circuit.X(16,nmos_device,'SB','SB_w','VSS' ,'VSS' , w='1', l='0.15')

    return circuit

# master slave flip flop
def ms_reg_gen(name):
    circuit = SubCircuit(name, 'VDD VSS clk D Q')
    circuit.X(0 ,nmos_device,'net3','clk' ,'VSS' ,'VSS',  l='0.15',w='0.42')
    circuit.X(8 ,pmos_device,'net3','clk' ,'VDD' ,'VDD',  l='0.15',w='0.42') 

    circuit.X(1 ,nmos_device,'net4','net2','net5','VSS',  l='0.15',w='0.42') 
    circuit.X(10,pmos_device,'Din' ,'net2','net1','VDD',  l='0.15',w='0.42') 

    circuit.X(2 ,nmos_device,'net55','Q' ,'VSS' ,'VSS',   l='0.15',w='0.42') 
    circuit.X(13,pmos_device,'net55','Q' ,'VDD' ,'VDD',   l='0.15',w='0.42') 

    circuit.X(3 ,nmos_device,'net2','net3','VSS' ,'VSS',  l='0.15',w='0.42')
    circuit.X(11,pmos_device,'net2','net3','VDD' ,'VDD',  l='0.15',w='0.42')

    circuit.X(5 ,nmos_device,'Din' ,'net3','net1','VSS',  l='0.15',w='0.42') 
    circuit.X(15,pmos_device,'net4','net3','net5','VDD',  l='0.15',w='0.42')  

    circuit.X(4 ,nmos_device,'Q' ,'net5','VSS' ,'VSS',    l='0.15',w='0.42')
    circuit.X(9 ,pmos_device,'Q' ,'net5','VDD' ,'VDD',    l='0.15',w='0.42') 
    
    circuit.X(6 ,nmos_device,'net11','net4','VSS' ,'VSS', l='0.15',w='0.42') 
    circuit.X(12,pmos_device,'net11','net4','VDD' ,'VDD', l='0.15',w='0.42') 

    circuit.X(7 ,nmos_device,'net4','net1','VSS' ,'VSS',  l='0.15',w='0.42') 
    circuit.X(14,pmos_device,'net4','net1','VDD' ,'VDD',  l='0.15',w='0.42')
    
    circuit.X(16 ,nmos_device,'net11'  ,'net2','net1','VSS',   l='0.15',w='0.42')
    circuit.X(17 ,pmos_device,'net11'  ,'net3','net1','VDD',   l='0.15',w='0.42')

    circuit.X(18 ,nmos_device,'net55'  ,'net3','net5','VSS',   l='0.15',w='0.42')
    circuit.X(19 ,pmos_device,'net55'  ,'net2','net5','VDD',   l='0.15',w='0.42')

    circuit.X(20 ,nmos_device,'D_'  ,'D','VSS','VSS',   l='0.15',w='0.42')
    circuit.X(21 ,pmos_device,'D_'  ,'D','VDD','VDD',   l='0.15',w='0.42')

    circuit.X(22 ,nmos_device,'Din'  ,'D_','VSS','VSS',   l='0.15',w='0.42')
    circuit.X(23 ,pmos_device,'Din'  ,'D_','VDD','VDD',   l='0.15',w='0.42')
              
    return circuit

# digital in digital out circuit with precharge, column select and read/write pass transsitors
def dido_gen(name, not_name, nand2_name):
    circuit = SubCircuit(name, 'VDD VSS PCHG WREN SEL BL BL_ DW DW_ DR DR_')
    circuit.X(0 ,pmos_device,'BL_' ,'net6','VDD','VDD',   l='0.15',w='1')
    circuit.X(1 ,pmos_device,'BL'  ,'net6','BL_','VDD',   l='0.15',w='1') 
    circuit.X(2 ,pmos_device,'BL'  ,'net6','VDD','VDD',   l='0.15',w='1') 
    circuit.X(3 ,pmos_device,'net6','net5','VDD','VDD',   l='0.15',w='0.42' )
    circuit.X(4 ,nmos_device,'net6','net5','VSS','VSS',   l='0.15',w='0.42' )
    circuit.X(5 ,pmos_device,'net5','PCHG' ,'VDD','VDD',  l='0.15',w='0.42' )
    circuit.X(6 ,nmos_device,'net5','PCHG' ,'VSS','VSS',  l='0.15',w='0.42' )
    circuit.X(7 ,pmos_device,'BL_' ,'net3','DR_','VDD',   l='0.15',w='0.5') 
    circuit.X(8 ,pmos_device,'DR'  ,'net3','BL' ,'VDD',   l='0.15',w='0.5') 
    circuit.X(9 ,pmos_device,'net4','SEL' ,'VDD','VDD',   l='0.15',w='0.42' )
    circuit.X(10,nmos_device,'BL'  ,'net2','DW' ,'VSS',   l='0.15',w='1' )
    circuit.X(11,nmos_device,'DW_' ,'net2','BL_','VSS',   l='0.15',w='1' )
    circuit.X(12,nmos_device,'net4','SEL' ,'VSS','VSS',   l='0.15',w='0.42' )
    circuit.X(13,nmos_device,'net3','net4','VSS','VSS',   l='0.15',w='0.42' )
    circuit.X(14,pmos_device,'net3','net4','VDD','VDD',   l='0.15',w='0.42' )
    circuit.X(15, nand2_name, 'VDD', 'VSS', 'net4', 'WREN', 'net1')
    circuit.X(16, not_name, 'VDD', 'VSS','net1', 'net2')
    return circuit

# row driver
def row_driver_cell(name, nand2_name):
    circuit = SubCircuit(name, 'VDD VSS WLEN A B')
    circuit.X(0,nand2_name,'VDD','VSS','A','WLEN','net1')
    circuit.X(1, pmos_device,'B', 'net1', 'VDD', 'VDD',  w='2', l='0.15')
    circuit.X(2, nmos_device,'B', 'net1', 'VSS', 'VSS',  w='2', l='0.15')
    return circuit

# control
def self_timed_ctrl(name, del_cell_name, not_name, nand2_name, nand3_name):
    ctrl = SubCircuit(name, 'VDD VSS clk cs write DBL DBL_ WREN PCHG WLEN SAEN')
    
    ctrl.X(0 ,pmos_device, 'net2','clk','VDD','VDD',     l='0.15',w='0.8' )
    ctrl.X(1 ,nmos_device, 'net2','clk','VSS','VSS',     l='0.15',w='0.8' )
    ctrl.X(2 ,pmos_device, 'WLENP','net2','VDD','VDD',    l='0.15',w='0.8' )
    ctrl.X(3 ,nmos_device, 'WLENP','net2','VSS','VSS',    l='0.15',w='0.8' )

    # always on PCHG during reads and neg edge
    ctrl.X(4, not_name, 'VDD', 'VSS', 'write', 'WREN_')
    ctrl.X(5, not_name, 'VDD', 'VSS', 'clk', 'clkp')
    ctrl.X(6, nand2_name,'VDD', 'VSS', 'clkp', 'WREN_', 'PCHGP')
    ctrl.X(7, not_name, 'VDD', 'VSS', 'PCHGP', 'PCHGPP')
    ctrl.X(8 ,pmos_device, 'PCHG','PCHGPP','VDD','VDD',    l='0.15',w='4' )
    ctrl.X(9 ,nmos_device, 'PCHG','PCHGPP','VSS','VSS',    l='0.15',w='2' )

    ctrl.X(10 ,pmos_device,'DBL_' ,'PCHG','VDD','VDD', l='0.15',w='0.42')
    ctrl.X(11 ,pmos_device,'DBL'  ,'PCHG','DBL_','VDD',l='0.15',w='0.42') 
    ctrl.X(12 ,pmos_device,'DBL'  ,'PCHG','VDD','VDD', l='0.15',w='0.42') 

    # word-line on if chipselect
    ctrl.X(13, nand2_name,  'VDD', 'VSS', 'cs', 'WLENP', 'WLENPP')
    ctrl.X(14, not_name,    'VDD', 'VSS', 'WLENPP', 'WLEN')

    # turn on sense amplifier
    ctrl.X(15, not_name,    'VDD', 'VSS', 'DBL_', 'RBL')
    ctrl.X(16, nand2_name,  'VDD', 'VSS','WLEN', 'RBL', 'SAEN_')

    ctrl.X(17 ,pmos_device, 'SAEN','SAEN_','VDD','VDD',    l='0.15',w='2' )
    ctrl.X(18 ,nmos_device, 'SAEN','SAEN_','VSS','VSS',    l='0.15',w='1' )

    ctrl.X(19 ,pmos_device, 'WREN','WREN_','VDD','VDD',    l='0.15',w='4' )
    ctrl.X(20 ,nmos_device, 'WREN','WREN_','VSS','VSS',    l='0.15',w='2' )
    return ctrl