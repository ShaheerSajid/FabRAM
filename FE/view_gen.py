import math
import sys
import time

import spice
import gds
##############################################################
# Arugment Parsing
##############################################################
n = len(sys.argv)
if n < 4:
    print("Error: Not enough arguments")
    print("Arguments: Num_Words Num_Bits Mux")
    exit()
else:
    #add this as arguments and check for valid inputs: (must be power of 2, must be within limits)
    #words >= 32
    mem_words   = int(sys.argv[1])
    #bits >= 4
    mem_bits    = int(sys.argv[2])
    #mux >= 4
    col_mux     = int(sys.argv[3])

    if (math.log(mem_words, 2).is_integer() == 0):
        print("Error: mem_words is not power of 2")
        exit()
    if (math.log(mem_bits, 2).is_integer() == 0):
        print("Error: mem_bits is not power of 2")
        exit()
    if (math.log(col_mux,2).is_integer() == 0):
        print("Error: col_mux is not power of 2")
        exit()

#rows
num_words = int(mem_words/col_mux)
#columns
num_bits = mem_bits*col_mux
top_name        = 'sram'+str(mem_words)+'x'+str(mem_bits)

print("\n")
print("Generating Views... "+top_name)
print("\n")

time_res = 1000000
##########################
# Spice
##########################
start_time = time.time()
spice.gen_spice(mem_words, mem_bits, col_mux)
end_time = time.time()
print(("Completed: Took {:.2f} ms".format((end_time-start_time)*1000)))

##########################
# GDS
##########################
start_time = time.time()
gds.gen_gds(mem_words, mem_bits, col_mux)
end_time = time.time()
print(("Completed: Took {:.2f} ms".format((end_time-start_time)*1000)))

##########################
# LEF
##########################

##########################
# LIB
##########################
