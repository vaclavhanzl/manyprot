# manyprot - Mapping protein conformation landscapes

You can have a look at our posters:
* ML4NGP 2025 in Warsaw, [Mapping Conformation Landscapes
hidden in ESMFold protein language models](https://drive.google.com/file/d/1AMM9-OdYmMUuoG0vgW1UG6zvoC4hENeW/view?usp=sharing)
* ML4NGP 2025 in Vilnius, [Noise Is All You Need](https://drive.google.com/file/d/1sKGB4QNUezTiU4pzB9scsGe4nFd8z0hW/view?usp=sharing)
  
If you have an idea for protein structure diversity source to be integrated with Manyprot, share it in [Discussions](https://github.com/vaclavhanzl/manyprot/discussions/1).

This project is in a design phase, though we have some code nearly ready. At the moment you may already enjoy Jupyter-pymol connection - just put jupymol.py to your project (proper mamba package to follow soon) and do:
```
%load_ext jupymol
from jupymol import pymol, pymol_3d_scatter, pymol_3d_line
```
and then you can use pymol(), %pymol and %%pymol in your Jupyter notebook.
