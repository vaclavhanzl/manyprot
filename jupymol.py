# jupymol: send commands from Jupyter to pymol, batching them in each cell
import xmlrpc.client
from IPython.core.magic import register_line_cell_magic
from IPython import get_ipython

pymol_socket = xmlrpc.client.ServerProxy("http://localhost:9123/RPC2") # expects "pymol -R" running, now or later
batch_pymol_text = "" # accumulated text

def send_pymol_batch():
    """
    Send commands accumulated by pymol(), %pymol and %%pymol
    """
    global batch_pymol_text
    n = len(batch_pymol_text.split("\n"))
    print(f'Sending {n} line{"s" if n>1 else ""} to pymol')
    pymol_socket.do(batch_pymol_text)
    batch_pymol_text = ""

def _flush_pymol_batch_after_cell(result=None):
    global batch_pymol_text
    if batch_pymol_text!="":
        try:
            send_pymol_batch()
        except Exception as e:
            print(f"[PyMOL auto-flush] {e}")

def load_ipython_extension(ip):
    """
    Initialize jupymol in notebook
    Called by %load_ext jupymol
    """
    global pymol
    @register_line_cell_magic # this also makes pymol() global
    def pymol(line, cell=None):
        global batch_pymol_text
        if cell is None:
            cell = line
        cell = cell.format(**get_ipython().user_ns)
        batch_pymol_text += cell+"\n"
    ip = get_ipython()
    ip.events.register("post_run_cell", _flush_pymol_batch_after_cell)
    print("pymol(), %pymol and %%pymol now send to pymol -R")



import numpy as np

def interpolate_colors_along_line(rgb, xyz):
    """
    Make color vector rgb the same size as the space coordinates vector xyz,
    interpolating colors in such a way that the color changes gradually along
    the length of the xyz polyline.

    Parameters
    ----------
    rgb : array-like
        Colors. Accepted shapes:
          - (M, 3)  RGB colors along the line (M can be 1, 2, ...).
          - (M, 4)  RGBA colors (alpha is preserved/interpolated too).
          - (3,) or (4,) a single color (broadcast to all vertices).
    xyz : array-like
        Polyline vertices in 2D or 3D. Shape (N, D), where D is 2 or 3.

    Returns
    -------
    np.ndarray
        Interpolated colors at each polyline vertex. Shape (N, C) where C is 3 or 4.
    """
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[0] < 1:
        raise ValueError("xyz must be a 2D array with shape (N, D), N >= 1.")

    rgb = np.asarray(rgb, dtype=float)

    # Normalize rgb to shape (M, C)
    if rgb.ndim == 1:
        if rgb.shape[0] not in (3, 4):
            raise ValueError("If rgb is 1D, it must have length 3 (RGB) or 4 (RGBA).")
        rgb = rgb[None, :]
    elif rgb.ndim == 2:
        if rgb.shape[1] not in (3, 4):
            raise ValueError("If rgb is 2D, it must have shape (M, 3) or (M, 4).")
    else:
        raise ValueError("rgb must be a 1D or 2D array.")

    n = xyz.shape[0]
    m, c = rgb.shape

    # If only one color provided, broadcast
    if m == 1:
        return np.repeat(rgb, n, axis=0)

    # Arc-length parameterization along the polyline
    if n == 1:
        # Single vertex: just return first color (or interpolate trivially)
        return np.repeat(rgb[:1], 1, axis=0)

    diffs = np.diff(xyz, axis=0)
    seg_lengths = np.linalg.norm(diffs, axis=1)
    cum = np.concatenate(([0.0], np.cumsum(seg_lengths)))
    total = cum[-1]

    # Handle degenerate polyline (all points identical)
    if total <= 0:
        return np.repeat(rgb[:1], n, axis=0)

    t_xyz = cum / total  # N samples in [0, 1]

    # Place provided colors uniformly along [0, 1]
    t_rgb = np.linspace(0.0, 1.0, m)

    # Interpolate each channel independently
    out = np.empty((n, c), dtype=float)
    for ch in range(c):
        out[:, ch] = np.interp(t_xyz, t_rgb, rgb[:, ch])

    return out


import numpy as np
from itertools import count
from collections import defaultdict
pymol_color_counter = 0
pymol_scatterplot_sizes = defaultdict(int) # to know where to go on for fresh=False

def make_pymol_color(r, g, b):
    global pymol_color_counter
    pymol_color_counter += 1
    new_color_name = f"mycolor{pymol_color_counter}"
    pymol(f"set_color {new_color_name}, [{r:.3f},{g:.3f},{b:.3f}]")
    return new_color_name

def pymol_reinitialize():
    """
    Reinitialize pymol and our related bookkeeping (custom colors)
    """
    global pymol_color_counter, pymol_scatterplot_sizes
    pymol("reinitialize")
    pymol_color_counter = 0
    pymol_scatterplot_sizes = defaultdict(int)

def pymol_3d_scatter(xyz, rgb=[0, 0, 1], name="scatterplot", radius=0.2, method="psd", fresh=True):
    """
    Drat 3D cloud of points as color balls in pymol
    method: "psd" - use pseudoatoms (preferred), "cgo" - use CGO (for huge sets)
    fresh: True - first delete any pymol object with this name
           False - add to object with this name if it already exists
    rgb: Either one color per vertex or just one color for all
    """
    # FIXME: Combination fresh==Falso and method=="cgo" is broken
    # TODO: Provide some way to overdraw point color without increasing radius
    global pymol_scatterplot_sizes
    if fresh:
        pymol_scatterplot_sizes[name] = 0
    xyz = np.asarray(xyz, dtype=float)
    rgb  = np.asarray(rgb,  dtype=float)
    if len(rgb.shape)==1: # One color for all the points
        rgb = np.broadcast_to(rgb, xyz.shape)
    assert xyz.ndim == 2 and xyz.shape[1] == 3
    assert rgb.ndim == 2 and rgb.shape[1] == 3
    assert len(xyz) == len(rgb)
    assert method in {"psd", "cgo"}
    if fresh:
        pymol(f"delete {name}")
    if method=="psd":
        for (x,y,z), (r,g,b) in zip(xyz, rgb):
            pymol_scatterplot_sizes[name] += 1
            n = pymol_scatterplot_sizes[name]
            color_name = make_pymol_color(r, g, b)
            pymol(f"pseudoatom {name}, pos=[{x},{y},{z}], color={color_name}, name=P{n}, resi={n}")
            atom_name = f"/{name}/PSDO/P/PSD`{n}/P{n}"  # this is how pymol names it
            pymol(f"set sphere_scale, {radius}, {atom_name}")
        pymol(f"show spheres, {name}")
        pymol(f"hide wire, {name}") # hide 3d "x" crosses
    elif method=="cgo":
        pymol("python")
        pymol("from pymol import cmd")
        pymol("from pymol.cgo import COLOR, SPHERE")
        pymol("obj = []")
        pymol(f"radius = {radius}")
        for (x,y,z), (r,g,b) in zip(xyz, rgb):
            pymol(f"obj.extend([COLOR,{r:.6f},{g:.6f},{b:.6f},SPHERE,{x:.6f},{y:.6f},{z:.6f},radius])")
        pymol(f"cmd.delete('{name}')")
        pymol(f"cmd.load_cgo(obj, '{name}')")
        pymol("python end")


from itertools import count
def pymol_3d_line(xyz, rgb=[1, 0, 0], name="polyline", radius=0.1, fresh=True):
    """
    Drat 3D polyline in pymol using cgo SAUSAGE objects
    fresh: True - first delete any pymol object with this name
           False - add to object with this name if it already exists
    rgb: either one color per vertex or just one color or two colors
         or any number of colors which will be interpolated
    """
    xyz = np.asarray(xyz, dtype=float)
    rgb  = np.asarray(rgb,  dtype=float)
    if len(rgb.shape)==1: # One color for the whole line
        rgb = np.broadcast_to(rgb, xyz.shape)
    elif rgb.shape[0]!=xyz.shape[0]: # Interpolate colors along the line
        rgb = interpolate_colors_along_line(rgb, xyz)
    assert xyz.ndim == 2 and xyz.shape[1] == 3
    assert rgb.ndim  == 2 and rgb.shape[1] == 3
    assert len(xyz) == len(rgb)
    if fresh:
        pymol(f"delete {name}")
    pymol("python")
    pymol("from pymol import cmd")
    pymol("from pymol.cgo import COLOR, SAUSAGE")
    pymol("obj = []")
    pymol(f"radius = {radius}")
    for (x,y,z), (x2,y2,z2), (r,g,b), (r2,g2,b2) in zip(xyz, xyz[1:], rgb, rgb[1:]):
        pymol(f"obj.extend([SAUSAGE,{x:.6f},{y:.6f},{z:.6f},{x2:.6f},{y2:.6f},{z2:.6f},{radius},{r:.6f},{g:.6f},{b:.6f},{r2:.6f},{g2:.6f},{b2:.6f}])")
    pymol(f"cmd.load_cgo(obj, '{name}')")
    pymol("python end")





















