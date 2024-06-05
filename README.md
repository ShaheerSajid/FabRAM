# FabRAM: Fabricable SRAM Compiler


FabRAM is an open-source and portable memory compiler that targets commercial foundries. This computer aided design tool allows generation and characterization of memory arrays for a given specification that are compatible with commercial EDA tools. 

FabRAM decouples the DRC effort made by the compiler to create cells and requires the designer to clean DRC before providing the cells to FabRAM. This reduces the information required by the compiler from the foundry and makes it more portable.
FabRAM has been designed to achieve the following objectives:

- Seamless generation of memories for a given specification
- Performing characterization
- Portability and flexibility across numerous technologies
- Give user control over implementation of various components in memory to address specific design constraints


 

In FabRAM, the designer is required to provide DRC clean cells. FabRAM requires layer width and spacing rules only to perform routing. This way we reduce the information required by the memory compiler from the foundry to simplify the routing algorithm. The routing algorithm does not need to incorporate new rules when switching technologies. This makes it easier to port FabRAM. Moreover, the designer can customize a variety of cells to meet design constraints.
<!--stackedit_data:
eyJoaXN0b3J5IjpbNTM0MzkzMTMwLC0zMzI0NTUzNjNdfQ==
-->