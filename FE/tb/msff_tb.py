import subprocess
import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Parser import SpiceParser
from PySpice.Spice.HighLevelElement import *
from PySpice.Unit import *

simulator = "ngspice"

time_unit = "u"

power = {
   "name":"VDD",
   "value":1.8
}
ground = {
   "name":"VSS",
   "value":0
}

simulation_steps = 2000

# 130nm : "/home/shaheer/Documents/pdks/130nm/130MSRFG/PDK/CadenceOA/t013mmsp001k3_1_4c/tsmc13rf_FSG_12v_25v_33v_T-013-MM-SP-001-K3_v1.4c_IC61_20120217/pdk13rf/models/hspice/rf013_v1d3.l"
# 65nm  : "/home/shaheer/Documents/pdks/65nm/65MSRFGP/PDK/CadenceOA/tn65cmsp018k3_1_0c/pdk/models/hspice/crn65gplus_2d5_lk_v1d0.l"
# sky130: "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"

models_lib = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
models_corner = "tt"
sram_netlist = "/home/shaheer/Desktop/FabRAM/FE/out/sram32x4.spi"

period = 3
steps = simulation_steps
max_time = 8.0*period
time_step = max_time/steps

sim_circuit = Circuit('characterizer')

sim_circuit.lib(models_lib, models_corner)
sim_circuit.include(sram_netlist)

sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
sim_circuit.V('clk',  "clk",  ground["name"] ,"DC 0V PULSE("+str(power["value"])+"V 0V 0n 1p 1p 1u 3u)")
sim_circuit.V('d',  "D",   ground["name"] ,"DC 0V PULSE("+str(power["value"])+"V 0V 17n 1p 1p 333n 777n)")
sim_str = """
.tran {step} {max}
.control
set hcopydevtype = svg
run
plot v(clk) v(D) v(Q)
.endc
""".format(step=str(time_step)+time_unit, 
          max=str(max_time)+time_unit)#period
sim_circuit.raw_spice = sim_str

sim_circuit.X(0, 'in_reg',power["name"],ground["name"], "clk", "D", "Q")
f = open("msff_tb.spi", "w")
f.write(str(sim_circuit))
f.close()

#run simulation
subprocess.call(["ngspice","msff_tb.spi"])