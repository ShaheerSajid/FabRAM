# FabRAM: Fabricable SRAM Compiler


FabRAM is an open-source and portable memory compiler that targets commercial foundries. This computer aided design tool allows generation and characterization of memory arrays for a given specification that are compatible with commercial EDA tools. 

FabRAM decouples the DRC effort made by the compiler to create cells and requires the designer to clean DRC before providing the cells to FabRAM. This reduces the information required by the compiler from the foundry and makes it more portable.
FabRAM has been designed to achieve the following objectives:

- Seamless generation of memories for a given specification
- Performing characterization
- Portability and flexibility across numerous technologies
- Give user control over implementation of various components in memory to address specific design constraints

FabRAM uses a tile based approach where, considering the typical architecture of an SRAM, a user may need to design and develop several components i.e., the bit cell, row driver, row and column decoders, input registers, control, digital-in/digital-out (DIDO), column multiplexer and sense amplifier
<!--stackedit_data:
eyJoaXN0b3J5IjpbMTE3NjgwNDkwLC0zMzI0NTUzNjNdfQ==
-->