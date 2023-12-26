#imports
import subprocess
import random
import math
import numpy as np
import matplotlib.pyplot as plt
import concurrent.futures
import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Parser import SpiceParser
from PySpice.Spice.HighLevelElement import *
from PySpice.Unit import *


#####################################################
# Settings
#####################################################
simulator = "ngspice"

#units and defaults
time_unit = "n"
cap_unit = "p"
pwr_unit = "u"
default_max_transition = 1.0
default_max_capacitance = 0.1

power = {
   "name":"VDD",
   "value":1.8
}
ground = {
   "name":"VSS",
   "value":0
}

table_size = 3
h_thresh = 0.9
c_thresh = 0.5
l_thresh = 0.1

simulation_steps = 2000

# 130nm : "/home/shaheer/Documents/pdks/130nm/130MSRFG/PDK/CadenceOA/t013mmsp001k3_1_4c/tsmc13rf_FSG_12v_25v_33v_T-013-MM-SP-001-K3_v1.4c_IC61_20120217/pdk13rf/models/hspice/rf013_v1d3.l"
# 65nm  : "/home/shaheer/Documents/pdks/65nm/65MSRFGP/PDK/CadenceOA/tn65cmsp018k3_1_0c/pdk/models/hspice/crn65gplus_2d5_lk_v1d0.l"
# sky130: "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"

models_lib = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
models_corner = "tt"
sram_netlist = "/home/shaheer/Desktop/FabRAM/FE/out/sram128x128.spi"

sram_cell = "sram128x128"
mem_words = 128
mem_bits = 128

addr_bits   = math.log2(mem_words)

#####################################################
# create array of input tr times
#####################################################
net_tr = []
val = default_max_transition
for i in range(table_size):
    net_tr.append(round(val,5))
    factor = random.uniform(1.5, 2.0)
    val = val/factor
net_tr.reverse()
print(net_tr)

#####################################################
# create array of output capacitances
#####################################################
cap_load = []
val = default_max_capacitance
for i in range(table_size):
    cap_load.append(round(val,5))
    factor = random.uniform(1.5, 2.0)
    val = val/factor
cap_load.reverse()
print(cap_load)
#create list of vars
simulation_params = []
for i in range(table_size):
  for j in range(table_size):
     simulation_params.append(((i,j), net_tr[i], cap_load[j]))
#remove files
try:
  subprocess.call('rm -rf log', shell=True)
  subprocess.call('mkdir log', shell=True)
except:
  pass
##########################################################
# Output Characterizer Function
##########################################################
def run_sim_output_characterizer(simulation_params):
  try:
    indexes = simulation_params[0]
    net_tr = simulation_params[1]
    cap_load = simulation_params[2]
    file_prefix = "log/sim_"+str(net_tr)+"_"+str(cap_load)
    print("Running: "+file_prefix)
    #create simulation template
    sim_circuit = Circuit('characterizer')

    sim_circuit.lib(models_lib, models_corner)
    sim_circuit.include(sram_netlist)

    sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
    sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
    #create pulse input
    rise = net_tr/(h_thresh-l_thresh)
    fall = net_tr/(h_thresh-l_thresh)
    pulse_width = 2.0*default_max_transition/(h_thresh-l_thresh)#add enough clock time pchg
    period = rise + (2.0*pulse_width) + fall
    sim_circuit.PulseVoltageSource('clk', 'clk', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_ns,
                                  rise_time = rise@u_ns,
                                  fall_time = fall@u_ns,
                                  pulse_width=pulse_width@u_ns, 
                                  period=period@u_ns)
    
    sim_circuit.PulseVoltageSource('addr', 'addr', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_s,
                                  rise_time = 1@u_ps,
                                  fall_time = 1@u_ps,
                                  pulse_width=pulse_width@u_ns, 
                                  period=2.0*period@u_ns)

    sim_circuit.PulseVoltageSource('din', 'din', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_s,
                                  rise_time = 1@u_ps,
                                  fall_time = 1@u_ps,
                                  pulse_width=pulse_width@u_ns, 
                                  period=2.0*period@u_ns)
    sim_circuit.PulseVoltageSource('write', 'write', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_s,
                                  rise_time = 1@u_ps,
                                  fall_time = 1@u_ps,
                                  pulse_width=2.0*period@u_ns, 
                                  period=4.0*period@u_ns)
    #create transient simulation
    steps = simulation_steps
    max_time = 4.0*period
    time_step = max_time/steps
    if(simulator == "spectre"):
      sim_str = """
      simulator lang=spectre
      .tran {step} {max} outputstart={savetime}
      """.format(step=str(time_step)+time_unit, 
                max=str(max_time)+time_unit,
                savetime = str(2.0*period)+time_unit)#period
    elif(simulator == "ngspice"):
      sim_str = """
      .tran {step} {max} {savetime}
      .control
      set hcopydevtype = svg
      run
      meas tran tdiff_cell_rise TRIG v(clk) VAL={c_thresh} RISE=3   TARG v(Q0) VAL={c_thresh} RISE=LAST 
      meas tran tdiff_tran_rise TRIG v(Q0)  VAL={l_thresh} RISE=LAST TARG v(Q0) VAL={h_thresh} RISE=LAST 
      meas tran tdiff_cell_fall TRIG v(clk) VAL={c_thresh} RISE=4 TARG v(Q0) VAL={c_thresh} FALL=LAST 
      meas tran tdiff_tran_fall TRIG v(Q0)  VAL={h_thresh} FALL=LAST TARG v(Q0) VAL={l_thresh} FALL=LAST 

      echo "$&tdiff_cell_rise,$&tdiff_tran_rise $&tdiff_cell_fall,$&tdiff_tran_fall" > {outfile}.text
      hardcopy {outfile}.svg v(clk)+10 v(x0.WLEN)+8 v(x0.DC0)+8 v(x0.WL0)+8 v(x0.DBL)+6 v(x0.DBL_)+6 v(x0.SAEN)+6 v(x0.BL0)+4 v(x0.BL_0)+4 v(x0.DR0)+2 v(x0.DR_0)+2 v(x0.DW0) v(x0.DW_0) v(x0.x6.x0.x0.q)-2 v(x0.x6.x0.x0.q_)-2 v(x0.x6.x127.x0.q)-4 v(x0.x6.x127.x0.q_)-4 v(Q0)-6 v(x0.WREN)-8
      exit
      .endc
      """.format(step=str(time_step)+time_unit, 
                max=str(max_time)+time_unit,
                savetime = str(2.0*0)+time_unit,
                outfile = file_prefix,
                l_thresh = l_thresh*power["value"],
                c_thresh = c_thresh*power["value"],
                h_thresh = h_thresh*power["value"])#period
    sim_circuit.raw_spice = sim_str


    addr_ports = ''
    for i in range(math.ceil((addr_bits))):
        addr_ports += ' addr' 
    #generate din ports
    din_ports = ''
    for i in range(mem_bits):
        din_ports += ' din'
    #generate dataout port list
    dout_ports = ''
    for i in range(mem_bits):
        dout_ports += ' Q'+str(i)
    port_str = power["name"] + ' ' + ground["name"] + ' clk' + addr_ports + din_ports + dout_ports + ' write ' + power["name"] + ' ' + sram_cell

    sim_circuit.X(0, port_str)
    #set cap
    cap = cap_load
    sim_circuit.C(0, 'Q0', ground["name"], str(cap)+cap_unit)
    f = open(file_prefix+".spi", "w")
    f.write(str(sim_circuit))
    f.close()

    #run simulation
    if(simulator == "spectre"):
      print ("unsupported")
      return
    elif (simulator == "ngspice"):
      subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
      #parse timing
      f = open(file_prefix+".text", "r")
      rise_fall = f.readline().split(" ")
      rise_vals = rise_fall[0].split(",")
      fall_vals = rise_fall[1].split(",")

      print(rise_vals,fall_vals)

    # rising
    slew = round(float(rise_vals[0])*1e9, 5)
    out_slew.append((indexes,slew))
    #transition times
    tr_time = round(float(rise_vals[1])*1e9, 5)
    out_tr.append((indexes,tr_time))

    # falling
    slew = round(float(fall_vals[0])*1e9, 5)
    out_slew_fall.append((indexes,slew))
    #transition times
    tr_time = round(float(fall_vals[1])*1e9, 5)
    out_tr_fall.append((indexes,tr_time))

    #find power as well internal power due to output driving load
    #find setup/hold
  except Exception as e: # work on python 3.x
    print(file_prefix)
    print(str(e))

##########################################################
# Setup Characterizer Function
##########################################################
def run_sim_setup_characterizer(simulation_params):
  try:
    indexes = simulation_params[0]
    net_tr_0 = simulation_params[1]
    net_tr_1 = simulation_params[2]
    file_prefix = "log/sim_"+str(net_tr_0)+"_"+str(net_tr_1)
    print("Running: "+file_prefix)
    
    #create pulse input
    rise_c = round(net_tr_0/(h_thresh-l_thresh),2)
    fall_c = round(net_tr_0/(h_thresh-l_thresh),2)

    rise_d = round(net_tr_1/(h_thresh-l_thresh),2)
    fall_d = round(net_tr_1/(h_thresh-l_thresh),2)

    pulse_width = round(2.0*default_max_transition/(h_thresh-l_thresh),2)#add enough clock time pchg
    period = round(rise_c + (2.0*pulse_width) + fall_c,2)
    period_d = round(rise_d + (2.0*pulse_width) + fall_d,2)
    
    #create transient simulation
    steps = simulation_steps
    max_time = 2*period
    time_step = max_time/steps

    start_offset = 0.8*rise_d
    clk_pos = 1.5*period+(rise_c/2)
    sweep_start = clk_pos-start_offset
    sweep_steps = 500
    sweep_step = start_offset/sweep_steps
    loop_break = False
    c2q_delay_prev = 0
    c2q_err = 0
    # print ("Starting at: ", sweep_start, sweep_step)
    while (1):
      #if sweet_start - sweep_end < 0.001 -> return setup time
      delay = sweep_start
      c2q_err = 0
      for itr in range(sweep_steps):
        #create simulation template
        sim_circuit = Circuit('characterizer')

        sim_circuit.lib(models_lib, models_corner)
        sim_circuit.include(sram_netlist)

        sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
        sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
        sim_circuit.V('clk',  "clk",  ground["name"] ,"DC 0V PULSE("+str(power["value"])+"V 0V 0n "+str(rise_c)+"n "+str(fall_c)+"n "+str(pulse_width)+"n "+str(period)+"n)")
        sim_circuit.V('d', "D", ground["name"] ,"DC 0V PULSE(0V "+str(power["value"])+" "+str(delay)+"n "+str(rise_d)+"n "+str(fall_d)+"n "+str(2*pulse_width)+"n "+str(2*period_d)+"n)")
        if(simulator == "spectre"):
          print ("unsupported")
          return
        elif(simulator == "ngspice"):
          sim_str = """
          .tran {step} {max} {savetime}
          .nodeset all = 0
          .control
          set hcopydevtype = svg
          run
          meas tran tdiff_c2q TRIG v(clk) VAL={c_thresh} RISE=1 TARG v(Q)   VAL={c_thresh} RISE=1 
          meas tran tdiff_d2c TRIG v(D)   VAL={c_thresh} RISE=1 TARG v(clk) VAL={c_thresh} RISE=1 
          echo "$&tdiff_c2q,$&tdiff_d2c" > {outfile}.text
          hardcopy {outfile}.svg v(clk) v(D) v(Q)
          exit
          .endc
          """.format(step=str(time_step)+time_unit, 
                    max=str(max_time)+time_unit,
                    savetime = str(period)+time_unit,
                    outfile = file_prefix+"_"+str(itr),
                    l_thresh = l_thresh*power["value"],
                    c_thresh = c_thresh*power["value"],
                    h_thresh = h_thresh*power["value"])#period
        sim_circuit.raw_spice = sim_str
        sim_circuit.X(0, 
                      'in_reg', 
                      power["name"], 
                      ground["name"], 
                      "clk",
                      "D", 
                      "Q"
                      )
        f = open(file_prefix+".spi", "w")
        f.write(str(sim_circuit))
        f.close()

        #run simulation
        if(simulator == "spectre"):
          print ("unsupported")
          return
        elif (simulator == "ngspice"):
          subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
          #parse timing
          f = open(file_prefix+"_"+str(itr)+".text", "r")
          vals = f.readline().split(",")
          # if first iteration and we got no value then we need to shift left start point
          if(itr == 0 and vals[0] == ""):
            start_offset = start_offset+0.05
            sweep_start = clk_pos-start_offset
            sweep_step = start_offset/sweep_steps
            loop_break = True
            break
          if(vals[0] == ""):
            d2q_delay = float(vals[1])
            setup_t = round(d2q_delay*1e9,5)
            setup_time.append((indexes,setup_t))
            return
          c2q_delay = float(vals[0])
          d2q_delay = float(vals[1])
          setup_t = round(d2q_delay*1e9,5)
          if (itr != 0):
            c2q_err = (c2q_delay-c2q_delay_prev)*100.0/abs(c2q_delay_prev)
          if(itr == 0):
            c2q_delay_prev = c2q_delay 
          print(vals, c2q_err)
          # if any other iteration we dont get a value then 
          if(c2q_err > 5):
            # start_offset = sweep_step
            sweep_start = delay-sweep_step
            sweep_step = sweep_step/sweep_steps
            print ("Starting at: ", sweep_start, sweep_step)
            loop_break = True
            break
          delay  = delay+sweep_step
          if(sweep_step < 1e-5):
            setup_time.append((indexes,setup_t))
            return
      if(loop_break == False):
        start_offset = start_offset-0.01
        sweep_start = clk_pos-start_offset
        sweep_step = start_offset/sweep_steps

  except Exception as e: # work on python 3.x
    print(file_prefix)
    print(str(e))

##########################################################
# Hold Characterizer Function
##########################################################
def run_sim_hold_characterizer(simulation_params):
  try:
    indexes = simulation_params[0]
    net_tr_0 = simulation_params[1]
    net_tr_1 = simulation_params[2]
    file_prefix = "log/sim_"+str(net_tr_0)+"_"+str(net_tr_1)
    print("Running: "+file_prefix)
    
    #create pulse input
    rise_c = round(net_tr_0/(h_thresh-l_thresh),2)
    fall_c = round(net_tr_0/(h_thresh-l_thresh),2)

    rise_d = round(net_tr_1/(h_thresh-l_thresh),2)
    fall_d = round(net_tr_1/(h_thresh-l_thresh),2)

    pulse_width = round(2.0*default_max_transition/(h_thresh-l_thresh),2)#add enough clock time pchg
    period = round(rise_c + (2.0*pulse_width) + fall_c,2)
    period_d = round(rise_d + (2.0*pulse_width) + fall_d,2)
    
    #create transient simulation
    steps = simulation_steps
    max_time = 2*period
    time_step = max_time/steps

    start_offset = 0.8*period_d
    clk_pos = 1.5*period+(rise_c/2)
    sweep_start = clk_pos-start_offset
    sweep_steps = 1000
    sweep_step = start_offset/sweep_steps
    loop_break = False
    # print ("Starting at: ", sweep_start, sweep_step)
    c2q_delay_prev =0
    c2q_err  =0
    while (1):
      #if sweet_start - sweep_end < 0.001 -> return setup time
      delay = sweep_start
      c2q_err = 0
      for itr in range(sweep_steps):
        #create simulation template
        sim_circuit = Circuit('characterizer')

        sim_circuit.lib(models_lib, models_corner)
        sim_circuit.include(sram_netlist)

        sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
        sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
        sim_circuit.V('clk',  "clk",  ground["name"] ,"DC 0V PULSE("+str(power["value"])+"V 0V 0n "+str(rise_c)+"n "+str(fall_c)+"n "+str(pulse_width)+"n "+str(period)+"n)")
        sim_circuit.V('d', "D", ground["name"] ,"DC 0V PULSE("+str(power["value"])+"V 0V "+str(delay)+"n "+str(rise_d)+"n "+str(fall_d)+"n "+str(2*pulse_width)+"n "+str(2*period_d)+"n)")

        if(simulator == "spectre"):
          print ("unsupported")
          return
        elif(simulator == "ngspice"):
          sim_str = """
          .tran {step} {max} {savetime}
          .control
          set hcopydevtype = svg
          run
          meas tran tdiff_c2q TRIG v(clk) VAL={c_thresh} RISE=1 TARG v(Q) VAL={c_thresh} FALL=1 
          meas tran tdiff_c2d TRIG v(clk) VAL={c_thresh} RISE=1 TARG v(D) VAL={c_thresh} RISE=1 
          echo "$&tdiff_c2q,$&tdiff_c2d" > {outfile}.text
          hardcopy {outfile}.svg v(clk) v(D) v(Q)
          exit
          .endc
          """.format(step=str(time_step)+time_unit, 
                    max=str(max_time)+time_unit,
                    savetime = str(period)+time_unit,
                    outfile = file_prefix+"_"+str(itr),
                    l_thresh = l_thresh*power["value"],
                    c_thresh = c_thresh*power["value"],
                    h_thresh = h_thresh*power["value"])#period
          
        sim_circuit.raw_spice = sim_str

        sim_circuit.X(0, 
                      'in_reg', 
                      power["name"], 
                      ground["name"], 
                      "clk",
                      "D", 
                      "Q"
                      )
        f = open(file_prefix+".spi", "w")
        f.write(str(sim_circuit))
        f.close()
    
        #run simulation
        if(simulator == "spectre"):
          print ("unsupported")
          return
        elif (simulator == "ngspice"):
          #print("Simulation using Ngspice")
          subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
          #parse timing
          f = open(file_prefix+"_"+str(itr)+".text", "r")
          vals = f.readline().split(",")
          # if first iteration and we got no value then we need to shift left start point
          if(itr == 0 and vals[0] == ""):
            print("Shifting")
            start_offset = start_offset-0.001
            sweep_start = clk_pos-start_offset
            sweep_step = start_offset/sweep_steps
            loop_break = True
            break
          if(vals[0] == ""):
            d2q_delay = float(vals[1])
            hold_t = round(d2q_delay*1e9,5)
            hold_time.append((indexes,hold_t))
            return
          c2q_delay = float(vals[0])
          d2q_delay = float(vals[1])
          hold_t = round(d2q_delay*1e9,5)
          if (itr != 0):
            c2q_err = (c2q_delay-c2q_delay_prev)*100.0/abs(c2q_delay_prev)
          if(itr == 0):
            c2q_delay_prev = c2q_delay
          print(vals, c2q_err)
          # if any other iteration we dont get a value then 
          if(c2q_err > 2):
            # start_offset = sweep_step
            sweep_start = delay+sweep_step
            sweep_step = sweep_step/sweep_steps
            print ("Starting at: ", sweep_start, sweep_step)
            loop_break = True
            break
          delay  = delay-sweep_step
          if(sweep_step < 1e-5):
            hold_time.append((indexes,hold_t))
            return
      if(loop_break == False):
        start_offset = start_offset+0.001
        sweep_start = clk_pos-start_offset
        sweep_step = start_offset/sweep_steps
  except Exception as e: # work on python 3.x
    print(file_prefix)
    print(str(e))

##########################################################
# Leakage Power Characterizer Function
##########################################################
def run_sim_leakage_characterizer():
  file_prefix = "log/sim_"+str(power["value"])+"_"+str(ground["value"])
  print("Running: "+file_prefix)

  sim_circuit = Circuit('characterizer')

  sim_circuit.lib(models_lib, models_corner)
  sim_circuit.include(sram_netlist)

  sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
  sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])

  steps = simulation_steps
  start_time = 2
  max_time = 5
  time_interval = (max_time - start_time)*1e-9
  time_step = max_time/steps


  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif(simulator == "ngspice"):
    sim_str = """
    .tran {step} {max} {savetime}
    .control
    set hcopydevtype = svg
    run
    meas tran yavg INTEG vgnd#branch from={savetime} to={max}
    echo "$&yavg" > {outfile}.text
    hardcopy {outfile}.svg vgnd#branch
    exit
    .endc
    """.format(step=str(time_step)+time_unit, 
              max=str(max_time)+time_unit,
              savetime=str(start_time)+time_unit,
              outfile = file_prefix)#period
    
  sim_circuit.raw_spice = sim_str


  addr_ports = ''
  for i in range(math.ceil((addr_bits))):
      addr_ports += ' '+ground["name"] 
  #generate din ports
  din_ports = ''
  for i in range(mem_bits):
      din_ports += ' '+ground["name"] 
  #generate dataout port list
  dout_ports = ''
  for i in range(mem_bits):
      dout_ports += ' Q'+str(i)
  port_str = power["name"] + ' ' + ground["name"] + ' '+ ground["name"] + addr_ports + din_ports + dout_ports + ' '+ground["name"]+' ' +ground["name"]+' ' + sram_cell
  
  sim_circuit.X(0, port_str)
  
  f = open(file_prefix+".spi", "w")
  f.write(str(sim_circuit))
  f.close()
  
  #run simulation
  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif (simulator == "ngspice"):
    #print("Simulation using Ngspice")
    subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    #get average current
    f = open(file_prefix+".text", "r")
    iavg = float(f.readline())
    leakage_pwr = round(float(power["value"])*iavg*1e3/time_interval,5)
    leakage_e = float(power["value"])*iavg*1e3
    return (leakage_pwr,leakage_e)

##########################################################
# Input Internal Power Characterizer Function
##########################################################
def run_sim_inputpwr_characterizer(simulation_params, clk=False):
  indexes = simulation_params[0]
  net_tr_0 = simulation_params[1]
  file_prefix = "log/sim_"+str(net_tr_0)
  print("Running: "+file_prefix)

  #create pulse input
  rise_c = round(net_tr_0/(h_thresh-l_thresh),2)
  fall_c = round(net_tr_0/(h_thresh-l_thresh),2)

  pulse_width = round(2.0*default_max_transition/(h_thresh-l_thresh),2)#add enough clock time pchg
  period = round(rise_c + (2.0*pulse_width) + fall_c,2)

  #create transient simulation
  steps = simulation_steps
  start_time = 0.5
  max_time = period
  time_interval = (max_time - start_time)*1e-9
  time_step = max_time/steps

  sim_circuit = Circuit('characterizer')

  sim_circuit.lib(models_lib, models_corner)
  sim_circuit.include(sram_netlist)

  sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
  sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
  sim_circuit.V('clk',  "clk",  ground["name"] ,"DC 0V PULSE(0V "+str(power["value"])+"V 1n "+str(rise_c)+"n "+str(fall_c)+"n "+str(pulse_width)+"n "+str(period)+"n)")
  if(clk == True):
    scale = 100
  else:
    scale = 1000
  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif(simulator == "ngspice"):
    sim_str = """
    .tran {step} {max} {savetime}
    .nodeset all = 0
    .control
    set hcopydevtype = svg
    run
    meas tran stt WHEN v(clk)={l_thresh} RISE=1
    meas tran stp WHEN v(clk)={h_thresh} RISE=1
    meas tran rise_i INTEG vgnd#branch from=stt to=stp

    let rise_pwr = rise_i * @vpower[dc] / (stp - stt)

    meas tran stt WHEN v(clk)={h_thresh} FALL=1
    meas tran stp WHEN v(clk)={l_thresh} FALL=1
    meas tran fall_i INTEG vgnd#branch from=stt to=stp

    let fall_pwr = fall_i * @vpower[dc] / (stp - stt)

    echo "$&rise_pwr,$&fall_pwr" > {outfile}.text
    hardcopy {outfile}.svg vgnd#branch v(clk)/{scale}
    exit
    .endc
    """.format(step=str(time_step)+time_unit, 
              max=str(max_time)+time_unit,
              savetime=str(start_time)+time_unit,
              l_thresh = l_thresh*power["value"],
              h_thresh = h_thresh*power["value"],
              scale = scale,
              outfile = file_prefix)#period
    
  sim_circuit.raw_spice = sim_str

  if(clk == True):
    addr_ports = ''
    for i in range(math.ceil((addr_bits))):
        addr_ports += ' '+ground["name"] 
    #generate din ports
    din_ports = ''
    for i in range(mem_bits):
        din_ports += ' '+ground["name"] 
    #generate dataout port list
    dout_ports = ''
    for i in range(mem_bits):
        dout_ports += ' Q'+str(i)
    port_str = power["name"] + ' ' + ground["name"] + ' clk' + addr_ports + din_ports + dout_ports + ' '+ground["name"]+' ' + ' ' + power["name"] + ' ' + sram_cell

    sim_circuit.X(0, port_str)
  else:
    addr_ports = ''
    for i in range(math.ceil((addr_bits))-1):
        addr_ports += ' '+ground["name"] 
    #generate din ports
    din_ports = ''
    for i in range(mem_bits):
        din_ports += ' '+ground["name"] 
    #generate dataout port list
    dout_ports = ''
    for i in range(mem_bits):
        dout_ports += ' Q'+str(i)
    port_str = power["name"] + ' ' + ground["name"] + ' ' + ground["name"] + ' clk' + addr_ports + din_ports + dout_ports + ' '+ground["name"]+' ' + power["name"] + ' ' + sram_cell

    sim_circuit.X(0, port_str)
  
  f = open(file_prefix+".spi", "w")
  f.write(str(sim_circuit))
  f.close()
 
  #run simulation
  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif (simulator == "ngspice"):
    #print("Simulation using Ngspice")
    subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    #get average current
    f = open(file_prefix+".text", "r")
    vals = f.readline().split(",")
    r_pwr = round(float(vals[0])*1e3,6)
    f_pwr = round(float(vals[1])*1e3,6)
    clk_pin_energy.append((indexes, r_pwr,f_pwr))

##########################################################
# Output Internal Power Characterizer Function
##########################################################
def run_sim_outputpwr_characterizer(simulation_params):
  indexes = simulation_params[0]
  cap_load = simulation_params[1]
  net_tr_0 = 1.0
  file_prefix = "log/sim_"+str(cap_load)+"_"+str(net_tr_0)
  print("Running: "+file_prefix)

  #create pulse input
  rise = round(net_tr_0/(h_thresh-l_thresh),2)
  fall = round(net_tr_0/(h_thresh-l_thresh),2)

  pulse_width = round(2.0*default_max_transition/(h_thresh-l_thresh),2)#add enough clock time pchg
  period = round(rise + (2.0*pulse_width) + fall,2)

  #create transient simulation
  steps = simulation_steps
  start_time = 2.0*period
  max_time = 4.0*period
  time_interval = (max_time - start_time)*1e-9
  time_step = max_time/steps

  sim_circuit = Circuit('characterizer')

  sim_circuit.lib(models_lib, models_corner)
  sim_circuit.include(sram_netlist)

  sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
  sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
  sim_circuit.PulseVoltageSource('clk', 'clk', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_ns,
                                  rise_time = rise@u_ns,
                                  fall_time = fall@u_ns,
                                  pulse_width=pulse_width@u_ns, 
                                  period=period@u_ns)
    
  sim_circuit.PulseVoltageSource('addr', 'addr', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=pulse_width@u_ns, 
                                period=2.0*period@u_ns)

  sim_circuit.PulseVoltageSource('din', 'din', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=pulse_width@u_ns, 
                                period=2.0*period@u_ns)
  sim_circuit.PulseVoltageSource('write', 'write', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=2.0*period@u_ns, 
                                period=4.0*period@u_ns)

  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif(simulator == "ngspice"):
    sim_str = """
    .tran {step} {max} {savetime}
    .nodeset all = 0
    .control
    set hcopydevtype = svg
    run
    meas tran stt WHEN v(Q0)={l_thresh} RISE=1
    meas tran stp WHEN v(Q0)={h_thresh} RISE=1
    meas tran rise_i INTEG vgnd#branch from=stt to=stp

    let rise_pwr = rise_i * @vpower[dc] / (stp - stt)

    meas tran stt WHEN v(Q0)={h_thresh} FALL=1
    meas tran stp WHEN v(Q0)={l_thresh} FALL=1
    meas tran fall_i INTEG vgnd#branch from=stt to=stp

    let fall_pwr = fall_i * @vpower[dc] / (stp - stt)

    echo "$&rise_pwr,$&fall_pwr" > {outfile}.text
    hardcopy {outfile}.svg vgnd#branch v(Q0)/100

    exit
    .endc
    """.format(step=str(time_step)+time_unit, 
              max=str(max_time)+time_unit,
              savetime = str(start_time)+time_unit,
              l_thresh = l_thresh*power["value"],
              h_thresh = h_thresh*power["value"],
              outfile = file_prefix)#period
    
  sim_circuit.raw_spice = sim_str

  
  addr_ports = ''
  for i in range(math.ceil((addr_bits))-1):
      addr_ports += ' '+ground["name"] 
  #generate din ports
  din_ports = ''
  for i in range(mem_bits-1):
      din_ports += ' '+ground["name"] 
  #generate dataout port list
  dout_ports = ''
  for i in range(mem_bits):
      dout_ports += ' Q'+str(i)
  port_str = power["name"] + ' ' + ground["name"] + ' clk' + addr_ports + ' addr din' + din_ports + dout_ports + ' write ' + power["name"] + ' ' +sram_cell

  sim_circuit.X(0, port_str)

  cap = cap_load
  sim_circuit.C(0, 'Q0', ground["name"], str(cap)+cap_unit)
  
  f = open(file_prefix+".spi", "w")
  f.write(str(sim_circuit))
  f.close()
 
  #run simulation
  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif (simulator == "ngspice"):
    #print("Simulation using Ngspice")
    subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    #get average current
    f = open(file_prefix+".text", "r")
    vals = f.readline().split(",")
    r_pwr = round(float(vals[0])*1e3,6)
    f_pwr = round(float(vals[1])*1e3,6)
    out_pin_energy.append((indexes, r_pwr,f_pwr))


##########################################################
# R/W power
##########################################################
def run_sim_rwpwr_characterizer(simulation_params):
  indexes = simulation_params[0]
  cap_load = simulation_params[1]
  net_tr_0 = 1.0
  file_prefix = "log/sim_"+str(cap_load)+"_"+str(net_tr_0)
  print("Running: "+file_prefix)

  #create pulse input
  rise = round(net_tr_0/(h_thresh-l_thresh),2)
  fall = round(net_tr_0/(h_thresh-l_thresh),2)

  pulse_width = round(2.0*default_max_transition/(h_thresh-l_thresh),2)#add enough clock time pchg
  period = round(rise + (2.0*pulse_width) + fall,2)

  #create transient simulation
  steps = simulation_steps
  start_time = 0
  max_time = 4.0*period
  time_interval = (max_time - start_time)*1e-9
  time_step = max_time/steps

  sim_circuit = Circuit('characterizer')

  sim_circuit.lib(models_lib, models_corner)
  sim_circuit.include(sram_netlist)

  sim_circuit.V('power', power["name"],ground["value"] ,power["value"])
  sim_circuit.V('gnd', ground["name"],ground["value"],ground["value"])
  sim_circuit.PulseVoltageSource('clk', 'clk', ground["name"], 
                                  initial_value=0@u_V, 
                                  pulsed_value=power["value"]@u_V,
                                  delay_time = 0@u_ns,
                                  rise_time = rise@u_ns,
                                  fall_time = fall@u_ns,
                                  pulse_width=pulse_width@u_ns, 
                                  period=period@u_ns)
    
  sim_circuit.PulseVoltageSource('addr', 'addr', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=pulse_width@u_ns, 
                                period=2.0*period@u_ns)

  sim_circuit.PulseVoltageSource('din', 'din', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=pulse_width@u_ns, 
                                period=2.0*period@u_ns)
  sim_circuit.PulseVoltageSource('write', 'write', ground["name"], 
                                initial_value=0@u_V, 
                                pulsed_value=power["value"]@u_V,
                                delay_time = 0@u_s,
                                rise_time = 1@u_ps,
                                fall_time = 1@u_ps,
                                pulse_width=2.0*period@u_ns, 
                                period=4.0*period@u_ns)

  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif(simulator == "ngspice"):
    sim_str = """
    .tran {step} {max} {savetime}
    .control
    set hcopydevtype = svg
    run
    meas tran stt WHEN v(clk)={c_thresh} RISE=1
    meas tran stp WHEN v(clk)={c_thresh} RISE=2
    meas tran write_1 INTEG vgnd#branch from=stt to=stp
    let write_1_pwr = write_1 * @vpower[dc] / (stp - stt)

    meas tran stt WHEN v(clk)={c_thresh} RISE=2
    meas tran stp WHEN v(clk)={c_thresh} RISE=3
    meas tran write_0 INTEG vgnd#branch from=stt to=stp
    let write_0_pwr = write_0 * @vpower[dc] / (stp - stt)

    meas tran stt WHEN v(clk)={c_thresh} RISE=3
    meas tran stp WHEN v(clk)={c_thresh} RISE=4
    meas tran read_1 INTEG vgnd#branch from=stt to=stp
    let read_1_pwr = read_1 * @vpower[dc] / (stp - stt)

    meas tran stt WHEN v(clk)={c_thresh} RISE=4
    let stp = {max}
    meas tran read_0 INTEG vgnd#branch from=stt to=stp
    let read_0_pwr = read_0 * @vpower[dc] / (stp - stt)

    echo "$&write_1_pwr,$&write_0_pwr $&read_1_pwr,$&read_0_pwr" > {outfile}.text

    hardcopy {outfile}.svg vgnd#branch v(Q0)/100 v(clk)/100

    exit
    .endc
    """.format(step=str(time_step)+time_unit, 
              max=str(max_time)+time_unit,
              savetime = str(start_time)+time_unit,
              c_thresh = c_thresh*power["value"],
              outfile = file_prefix)#period
    
  sim_circuit.raw_spice = sim_str

  addr_ports = ''
  for i in range(math.ceil((addr_bits))-1):
      addr_ports += ' '+ground["name"] 
  #generate din ports
  din_ports = ''
  for i in range(mem_bits-1):
      din_ports += ' '+ground["name"] 
  #generate dataout port list
  dout_ports = ''
  for i in range(mem_bits):
      dout_ports += ' Q'+str(i)
  port_str = power["name"] + ' ' + ground["name"] + ' clk' + addr_ports + ' addr din' + din_ports + dout_ports + ' write ' + power["name"] + ' ' +sram_cell

  sim_circuit.X(0, port_str)

  cap = cap_load
  sim_circuit.C(0, 'Q0', ground["name"], str(cap)+cap_unit)
  
  f = open(file_prefix+".spi", "w")
  f.write(str(sim_circuit))
  f.close()

  #run simulation
  if(simulator == "spectre"):
    print ("unsupported")
    return
  elif (simulator == "ngspice"):
    #print("Simulation using Ngspice")
    subprocess.call(["ngspice",file_prefix+".spi"],stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    #get average current
    f = open(file_prefix+".text", "r")
    write_read = f.readline().split(" ")
    write_vals = write_read[0]
    read_vals = write_read[1]
    r_w_pwr.append(write_read)

##########################################################
# Run Characterizer
##########################################################
# get sram size as input to script
# print starting message
print("###################################################")
print("Running Characterization of "+sram_cell)
print("###################################################")
##########################################################
# Ouput
##########################################################
print("#########################")
print("Output Characterization")
# Find tr/slew
out_tr = []
out_slew = []
out_tr_fall = []
out_slew_fall = []
run_sim_output_characterizer(simulation_params[0])
# print(run_sim_leakage_characterizer())
exit()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_sim_output_characterizer, simulation_params)

#construct table
rise_transition = [[0 for x in range(table_size)] for y in range(table_size)]
cell_rise = [[0 for x in range(table_size)] for y in range(table_size)] 
fall_transition = [[0 for x in range(table_size)] for y in range(table_size)]
cell_fall = [[0 for x in range(table_size)] for y in range(table_size)] 

for item in out_tr:
  rise_transition[item[0][0]][item[0][1]] = item[1]
for item in out_slew:
  cell_rise[item[0][0]][item[0][1]] = item[1]
for item in out_tr_fall:
  fall_transition[item[0][0]][item[0][1]] = item[1]
for item in out_slew_fall:
  cell_fall[item[0][0]][item[0][1]] = item[1]


print("Cell Rise")
for row in cell_rise:
   print(row)
print("Rise Transition")
for row in rise_transition:
   print(row)
print("Cell Fall")
for row in cell_fall:
   print(row)
print("Fall Transition")
for row in fall_transition:
   print(row)
###########################################################
# Find Setup/Hold
###########################################################
print("#########################")
print("Setup Characterization")

# setup_time = []
# hold_time = []

# simulation_params = []
# for i in range(table_size):
#   for j in range(table_size):
#      simulation_params.append(((i,j), net_tr[i], net_tr[j]))

# for params in simulation_params:
#   run_sim_setup_characterizer(params)
# stp_time = [[0 for x in range(table_size)] for y in range(table_size)] 
# for item in setup_time:
#   stp_time[item[0][0]][item[0][1]] = item[1]
# print("Setup Time")
# for row in stp_time:
#   print(row)

print("#########################")
print("Hold Characterization")
# for params in simulation_params:
#   run_sim_hold_characterizer(params)
# hld_time = [[0 for x in range(table_size)] for y in range(table_size)] 
# for item in hold_time:
#   hld_time[item[0][0]][item[0][1]] = item[1]
# print("Hold Time")
# for row in hld_time:
#   print(row)
###########################################################
# Find Leakage
###########################################################
print("#########################")
print("Leakage Power")
print(run_sim_leakage_characterizer())
###########################################################
# Find Clock pin power
###########################################################
print("#########################")
print("CLK pin Power")

simulation_params = []
setting = []
for i in range(table_size):
  simulation_params.append((i, net_tr[i]))
  setting.append(True)

clk_pin_energy  = []

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_sim_inputpwr_characterizer, simulation_params,setting)

print(clk_pin_energy)
##############################
#############################
# Find Input pin power
###########################################################
print("#########################")
print("Input pin Power")

clk_pin_energy  = []
setting = []
for i in range(table_size):
  setting.append(False)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_sim_inputpwr_characterizer, simulation_params,setting)
print(clk_pin_energy)
###########################################################
# Find Output pin power
###########################################################
print("#########################")
print("Output pin Power")

simulation_params = []
for i in range(table_size):
  simulation_params.append((i, cap_load[i]))

out_pin_energy  = []

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_sim_outputpwr_characterizer, simulation_params)
print(out_pin_energy)

###########################################################
# Find R/W power
###########################################################
print("#########################")
print("Write/Read Power")

r_w_pwr = []

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_sim_rwpwr_characterizer, simulation_params)
print(r_w_pwr)

