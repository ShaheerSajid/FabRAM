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

nmos_device     = "nch"
pmos_device     = "pch"

W_nand = 200e-9
L_nand = 60e-9
W_not  = 200e-9
L_not  = 60e-9
ratio  = 1.0

W_del       = 200e-9
L_del       = 5e-7
ratio_del   = 2.0
##############################################################
# Primitives
##############################################################
# not gate
def notg(name, W,L, ratio):
    circuit = SubCircuit('not'+name, 'VDD VSS A B')
    circuit.M(0, 'B', 'A', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(1, 'B', 'A', 'VSS', 'VSS', model=nmos_device, w=W, l=L)
    return circuit

# 2 input nand
def nand2(name, W,L, ratio):
    circuit = SubCircuit('nand2'+name, 'VDD VSS A B Y')
    circuit.M(0, 'Y', 'A', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(1, 'Y', 'B', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(2, 'Y', 'B', 'net1', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(3, 'net1', 'A', 'VSS', 'VSS', model=nmos_device, w=W, l=L)
    return circuit

# 3 input nand
def nand3(name, W,L, ratio):
    circuit = SubCircuit('nand3'+name, 'VDD VSS A B C Y')
    circuit.M(0, 'Y', 'A', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(1, 'Y', 'B', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(2, 'Y', 'C', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(3, 'Y', 'A', 'net1', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(4, 'net1', 'B', 'net2', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(5, 'net2', 'C', 'VSS', 'VSS', model=nmos_device, w=W, l=L)
    return circuit

# 4 input nand
def nand4(name, W,L, ratio):
    circuit = SubCircuit('nand4'+name, 'VDD VSS A B C Y')
    circuit.M(0, 'Y', 'A', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(1, 'Y', 'B', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(2, 'Y', 'C', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(3, 'Y', 'D', 'VDD', 'VDD', model=pmos_device, w=ratio*W, l=L)
    circuit.M(4, 'Y', 'D', 'net1', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(5, 'net1', 'B', 'net2', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(6, 'net2', 'C', 'net3', 'VSS', model=nmos_device, w=W, l=L)
    circuit.M(7, 'net3', 'A', 'VSS', 'VSS', model=nmos_device, w=W, l=L)
    return circuit

##############################################################
# Memory Bricks
##############################################################
# Bit cell
def bit_cell_gen(name):
    circuit = SubCircuit(name, 'VDD VSS WL BL BL_')
    circuit.M(0, 'Q','Q_','VSS','VSS', model=nmos_device,   w='0.2U' ,l='0.065U')
    circuit.M(1, 'Q_','Q','VSS','VSS', model=nmos_device,   w='0.2U' ,l='0.065U')
    circuit.M(2, 'Q','Q_','VDD','VDD', model=pmos_device,   w='0.12U',l='0.065U')
    circuit.M(3, 'Q_','Q','VDD','VDD', model=pmos_device,   w='0.12U',l='0.065U')
    circuit.M(4, 'Q','WL','BL' ,'VSS', model=nmos_device,   w='0.16U',l='0.075U')
    circuit.M(5, 'Q_','WL','BL_','VSS', model=nmos_device,  w='0.16U',l='0.075U')
    return circuit

# sense amplifier
def sense_amp_gen(name):
    circuit = SubCircuit(name, 'VDD VSS SAEN BL BL_ SB')
    circuit.M(0,'net1' ,'SAEN' ,'VSS' ,'VSS' ,model=nmos_device,    w='0.4u', l='0.06u')
    circuit.M(1,'diff1','BL_'  ,'net1','net1',model=nmos_device,    w='0.2U', l='0.06U')
    circuit.M(2,'diff2','BL'   ,'net1','net1',model=nmos_device,    w='0.2U', l='0.06U')
    circuit.M(3,'diff1','diff1','VDD' ,'VDD' ,model=pmos_device,    w='0.2U', l='0.06U')
    circuit.M(4,'diff2','diff1','VDD' ,'VDD' ,model=pmos_device,    w='0.2U', l='0.06U')
    circuit.M(5,'diff2_','diff2','VDD' ,'VDD' ,model=pmos_device,   w='0.4U', l='0.06U')
    circuit.M(6,'diff2_','diff2','VSS' ,'VSS' ,model=nmos_device,   w='0.2U', l='0.06U')
    circuit.M(7,'SB_'   ,'diff2_','VDD' ,'VDD' ,model=pmos_device,  w='0.8U', l='0.06U')
    circuit.M(8,'SB_'   ,'diff2_','VSS' ,'VSS' ,model=nmos_device,  w='0.8U', l='0.06U')

    circuit.M(9, 'SB_w','Q_','VSS','VSS', model=nmos_device,        w='0.2U' ,l='0.065U')
    circuit.M(10, 'Q_','SB_w','VSS','VSS', model=nmos_device,       w='0.2U' ,l='0.065U')
    circuit.M(11, 'SB_w','Q_','VDD','VDD', model=pmos_device,       w='0.12U',l='0.065U')
    circuit.M(12, 'Q_','SB_w','VDD','VDD', model=pmos_device,       w='0.12U',l='0.065U')
    circuit.M(13, 'SB_w','SAEN','SB_' ,'VSS', model=nmos_device,    w='0.16U',l='0.075U')
    circuit.M(14, 'Q_','SAEN','diff2_','VSS', model=nmos_device,    w='0.16U',l='0.075U')

    circuit.M(15,'SB','SB_w','VDD' ,'VDD' ,model=pmos_device, w='0.8U', l='0.06U')
    circuit.M(16,'SB','SB_w','VSS' ,'VSS' ,model=nmos_device, w='0.8U', l='0.06U')

    return circuit

# master slave flip flop
def ms_reg_gen(name):
    circuit = SubCircuit(name, 'VDD VSS clk D Q')
    circuit.M(0 ,'net3','clk' ,'VSS' ,'VSS',model=nmos_device,  l='60n',w='400n')
    circuit.M(1 ,'net4','net2','net5','VSS',model=nmos_device,  l='60n',w='400n') 
    circuit.M(2 ,'net55','Q' ,'VSS' ,'VSS',model=nmos_device,    l='60n',w='200n') 
    circuit.M(3 ,'net2','net3','VSS' ,'VSS',model=nmos_device,  l='60n',w='400n') 
    circuit.M(4 ,'Q' ,'net5','VSS' ,'VSS',model=nmos_device,    l='60n',w='400n') 
    circuit.M(5 ,'Din'  ,'net3','net1','VSS',model=nmos_device,   l='60n',w='400n') 
    circuit.M(6 ,'net11','net4','VSS' ,'VSS',model=nmos_device,  l='60n',w='200n') 
    circuit.M(7 ,'net4','net1','VSS' ,'VSS',model=nmos_device,  l='60n',w='400n') 
    circuit.M(8 ,'net3','clk' ,'VDD' ,'VDD',model=pmos_device,  l='60n',w='400n') 
    circuit.M(9 ,'Q' ,'net5','VDD' ,'VDD',model=pmos_device,    l='60n',w='400n') 
    circuit.M(10,'Din'  ,'net2','net1','VDD',model=pmos_device,   l='60n',w='400n') 
    circuit.M(11,'net2','net3','VDD' ,'VDD',model=pmos_device,  l='60n',w='400n') 
    circuit.M(12,'net11','net4','VDD' ,'VDD',model=pmos_device,  l='60n',w='200n') 
    circuit.M(13,'net55','Q' ,'VDD' ,'VDD',model=pmos_device,    l='60n',w='200n') 
    circuit.M(14,'net4','net1','VDD' ,'VDD',model=pmos_device,  l='60n',w='400n') 
    circuit.M(15,'net4','net3','net5','VDD',model=pmos_device,  l='60n',w='400n') 

    circuit.M(16 ,'net11'  ,'net2','net1','VSS',model=nmos_device,   l='60n',w='400n')
    circuit.M(17 ,'net11'  ,'net3','net1','VDD',model=pmos_device,   l='60n',w='400n')

    circuit.M(18 ,'net55'  ,'net3','net5','VSS',model=nmos_device,   l='60n',w='400n')
    circuit.M(19 ,'net55'  ,'net2','net5','VDD',model=pmos_device,   l='60n',w='400n')

    circuit.M(20 ,'D_'  ,'D','VSS','VSS',model=nmos_device,   l='60n',w='200n')
    circuit.M(21 ,'D_'  ,'D','VDD','VDD',model=pmos_device,   l='60n',w='200n')

    circuit.M(22 ,'Din'  ,'D_','VSS','VSS',model=nmos_device,   l='60n',w='400n')
    circuit.M(23 ,'Din'  ,'D_','VDD','VDD',model=pmos_device,   l='60n',w='400n')
              
    return circuit

# digital in digital out circuit with precharge, column select and read/write pass transsitors
def dido_gen(name, not_name, nand2_name):
    circuit = SubCircuit(name, 'VDD VSS PCHG WREN SEL BL BL_ DW DW_ DR DR_')
    circuit.M(0 ,'BL_' ,'net6','VDD','VDD',model=pmos_device,   l='60n',w='660.0n')
    circuit.M(1 ,'BL'  ,'net6','BL_','VDD',model=pmos_device,   l='60n',w='660.0n') 
    circuit.M(2 ,'BL'  ,'net6','VDD','VDD',model=pmos_device,   l='60n',w='660.0n') 
    circuit.M(3 ,'net6','net5','VDD','VDD',model=pmos_device,   l='60n',w='200n' )
    circuit.M(4 ,'net6','net5','VSS','VSS',model=nmos_device,   l='60n',w='200n' )
    circuit.M(5 ,'net5','PCHG' ,'VDD','VDD',model=pmos_device,  l='60n',w='200n' )
    circuit.M(6 ,'net5','PCHG' ,'VSS','VSS',model=nmos_device,  l='60n',w='200n' )
    circuit.M(7 ,'BL_' ,'net3','DR_','VDD',model=pmos_device,   l='60n',w='660.0n') 
    circuit.M(8 ,'DR'  ,'net3','BL' ,'VDD',model=pmos_device,   l='60n',w='660.0n') 
    circuit.M(9 ,'net4','SEL' ,'VDD','VDD',model=pmos_device,   l='60n',w='200n' )
    circuit.M(10,'BL'  ,'net2','DW' ,'VSS',model=nmos_device,   l='60n',w='1u' )
    circuit.M(11,'DW_' ,'net2','BL_','VSS',model=nmos_device,   l='60n',w='1u' )
    circuit.M(12,'net4','SEL' ,'VSS','VSS',model=nmos_device,   l='60n',w='200n' )
    circuit.M(13,'net3','net4','VSS','VSS',model=nmos_device,   l='60n',w='200n' )
    circuit.M(14,'net3','net4','VDD','VDD',model=pmos_device,   l='60n',w='200n' )
    circuit.X(0, nand2_name, 'VDD', 'VSS', 'net4', 'WREN', 'net1')
    circuit.X(1, not_name, 'VDD', 'VSS','net1', 'net2')
    return circuit

# row driver
def row_driver_cell(name, nand2_name):
    circuit = SubCircuit(name, 'VDD VSS WLEN A B')
    circuit.X(0,nand2_name,'VDD','VSS','A','WLEN','net1')
    circuit.M(0, 'B', 'net1', 'VDD', 'VDD', model=pmos_device, w='40u', l='60n')
    circuit.M(1, 'B', 'net1', 'VSS', 'VSS', model=nmos_device, w='40u', l='60n')
    return circuit

# control
def self_timed_ctrl(name, del_cell_name, not_name):
    ctrl = SubCircuit(name, 'VDD VSS clk WREN PCHG WLEN SAEN')
    #PULSE  pch
    ctrl.X(0, del_cell_name, 'VDD', 'VSS', 'clk', 'PCHG_')
    ctrl.X(1, not_name, 'VDD', 'VSS', 'PCHG_', 'PCHG')
    #turn on wl
    ctrl.X(2, del_cell_name, 'VDD', 'VSS', 'PCHG', 'WLEN_pulse')
    ctrl.X(3, not_name, 'VDD', 'VSS', 'WLEN_pulse', 'WLEN_pulse_')
    #latch wlen RST
    ctrl.M(0 ,'net2','RST',       'VDD','VDD',model=pmos_device,l='60n',w='800n' )
    ctrl.M(1 ,'net2','WLEN_pulse','VSS','VSS',model=nmos_device,l='60n',w='800n' )
    #latch
    #should be strong inverter
    ctrl.M(2 ,'WLEN','net2','VDD','VDD',model=pmos_device,      l='60n',w='800n' )
    ctrl.M(3 ,'WLEN','net2','VSS','VSS',model=nmos_device,      l='60n',w='800n' )
    #should be weak inverter
    ctrl.M(6 ,'net2','RST','net1','VSS',model=nmos_device,      l='60n',w='800n' )
    ctrl.M(4 ,'net1','WLEN','VDD','VDD',model=pmos_device,      l='60n',w='400n' )
    ctrl.M(5 ,'net1','WLEN','VSS','VSS',model=nmos_device,      l='60n',w='400n' )
    #turn on se
    ctrl.X(4, del_cell_name, 'VDD', 'VSS', 'WLEN_pulse_', 'SAEN_pulse')
    #latch wlen RST
    ctrl.M(7 ,'net4','RST',       'VDD','VDD',model=pmos_device,l='60n',w='800n' )
    ctrl.M(8 ,'net4','SAEN_pulse','VSS','VSS',model=nmos_device,l='60n',w='800n' )
    #latch
    #should be strong inverter
    ctrl.M(9 ,'SAEN','net4','VDD','VDD',model=pmos_device,      l='60n',w='800n' )
    ctrl.M(10 ,'SAEN','net4','VSS','VSS',model=nmos_device,     l='60n',w='800n' )
    #should be weak inverter
    ctrl.M(11 ,'net4','RST','net3','VSS',model=nmos_device,     l='60n',w='800n' )
    ctrl.M(12,'net3','SAEN','VDD','VDD',model=pmos_device,      l='60n',w='400n' )
    ctrl.M(13 ,'net3','SAEN','VSS','VSS',model=nmos_device,     l='60n',w='400n' )
    #turn on rst
    #reset on negedge
    ctrl.X(5, not_name, 'VDD', 'VSS', 'clk', 'clk_')
    ctrl.X(6, del_cell_name, 'VDD', 'VSS', 'clk_', 'RST_')
    ctrl.X(7, not_name, 'VDD', 'VSS', 'RST_', 'RST')
    return ctrl