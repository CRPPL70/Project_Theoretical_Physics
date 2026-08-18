# === IMPORTS ===
# Standard library imports
from sys import argv
import os
import ctypes

# Third party imports
import numpy as np
import sympy as sp
from sympy.physics.mechanics import dynamicsymbols

# Local imports
import cprototype as cp
import animation as anim
from ccompiler import CSharedLibraryCompiler
from lagrangian import LagrangianToC

# === CONSTANTS ===
if len(argv) > 1:
    try:
        NUMBER_OF_PARTICLES = int(argv[1]) # Number of particles read from command line
    except ValueError as e:
        print(e)
        NUMBER_OF_PARTICLES = np.random.randint(1,23)
        print(f"Number of particles is now set to randomly chosen: {NUMBER_OF_PARTICLES}")
else:
    NUMBER_OF_PARTICLES = 12     # Number of particles in the simulation
RADIUS              = 2.0    # Initial radius for particle placement
dt                  = 0.01   # Timestep for the simulation

# === 1. DEFINE LAGRANGIAN AND GENERATE C CODE ON THE FLY ===
print("Generating Lagrangian mechanics C code on the fly...")

# 1a. Define symbols (e.g., a 2D harmonic oscillator representing an attractive central force)
x, y = dynamicsymbols('x y')
m_sym, k_sym = sp.symbols('m k')

# Kinetic Energy: T = 1/2 m (v_x^2 + v_y^2)
T = 0.5 * m_sym * (x.diff()**2 + y.diff()**2)

# Potential Energy: V = 1/2 k (x^2 + y^2) 
V = 0.5 * k_sym * (x**2 + y**2)

L = T - V

# Substitute physical constants directly to simplify the C signature
L = L.subs({m_sym: 1.0, k_sym: 5.0})

# 1b. Use LagrangianToC
gen = LagrangianToC(L, [x, y])
c_equations = gen.generate_c_function("generated_eqs", collapse_constants=True)

# 1c. Wrap the generated code to bridge the float* generator with the Vector2D* multi-particle arrays
wrapper_c_code = f"""#include "../solver/solver.c"

{c_equations}

/* Adapter that bridges the single-particle float array logic to Vector2D arrays */
void dfdx_wrapper(Vector2D* q, Vector2D* dq, Vector2D* _dq, Vector2D* _ddq, float t, size_t N) {{
    for(size_t i=0; i<N; ++i) {{
        float temp_q[2]    = {{q[i].x, q[i].y}};
        float temp_dq[2]   = {{dq[i].x, dq[i].y}};
        float temp__dq[2]  = {{0.0f, 0.0f}};
        float temp__ddq[2] = {{0.0f, 0.0f}};

        // N=2 internally since a single 2D particle has 2 degrees of freedom (x, y)
        generated_eqs(temp_q, temp_dq, temp__dq, temp__ddq, t, 2);

        _dq[i].x  = temp__dq[0];
        _dq[i].y  = temp__dq[1];
        _ddq[i].x = temp__ddq[0];
        _ddq[i].y = temp__ddq[1];
    }}
}}
"""

# 1d. Write the customized code to a temporary C file
on_the_fly_src = "on_the_fly.c"
with open(on_the_fly_src, "w") as f:
    f.write(wrapper_c_code)

# === 2. C LIBRARY COMPILATION & LOADING ===
print("Compiling the generated C code...")
ccompiler = CSharedLibraryCompiler(source_file=on_the_fly_src)
__solver_path = ccompiler.compile()
_libsolver    = cp.EOMSolver(__solver_path, NUMBER_OF_PARTICLES, DIMENSIONS=2)

# === 3. SET UP CALLBACK FUNCTION FOR NEXT_2D ===
# Inform ctypes of the signature of the injected C wrapper: void(*f)(Vector2D*,Vector2D*,Vector2D*,Vector2D*,float,size_t)
CALLBACK_TYPE = ctypes.CFUNCTYPE(
    None, 
    ctypes.POINTER(cp.Vector2D), ctypes.POINTER(cp.Vector2D), 
    ctypes.POINTER(cp.Vector2D), ctypes.POINTER(cp.Vector2D), 
    ctypes.c_float, ctypes.c_size_t
)

# Extract the wrapped function pointer from the compiled `.so` library
dfdx_c_func = getattr(_libsolver.lib, "dfdx_wrapper")
cb_func = CALLBACK_TYPE(dfdx_c_func)

# Override argtypes for next_step (which currently maps to next_2D)
_libsolver.next_step.argtypes = [
    _libsolver.c_vec_ptr, _libsolver.c_vec_ptr,
    _libsolver.c_vec_ptr, _libsolver.c_vec_ptr,
    ctypes.c_float, ctypes.c_float, ctypes.c_size_t, CALLBACK_TYPE
]

# Provide a Python wrapper to bridge our 8-argument C call back to the 6-argument layout expected by Animation2D
def custom_next_step(pos, vel, new_pos, new_vel, dt, N):
    t = 0.0  # Time variable for an autonomous physical system
    _libsolver.next_step(pos, vel, new_pos, new_vel, t, dt, N, cb_func)


# === INITIAL CONDITIONS ===
positions = [_libsolver.vector(x=RADIUS * np.cos(2 * np.pi * i / NUMBER_OF_PARTICLES),
                               y=RADIUS * np.sin(2 * np.pi * i / NUMBER_OF_PARTICLES))
             for i in range(NUMBER_OF_PARTICLES)]
# Add rotational velocity for a beautiful visual path
velocities = [_libsolver.vector(x=-np.sin(2 * np.pi * i / NUMBER_OF_PARTICLES), 
                                y=np.cos(2 * np.pi * i / NUMBER_OF_PARTICLES)) 
              for i in range(NUMBER_OF_PARTICLES)]

# === PLOTTING SETUP ===
ani = anim.Animation2D(vector_factory=_libsolver.vector,
                       c_arr=_libsolver.c_arr,
                       next_step=custom_next_step, # Route to our newly defined wrapper
                       positions=positions,
                       velocities=velocities,
                       dt=dt,
                       NUMBER_OF_PARTICLES=NUMBER_OF_PARTICLES)
ani.create_canvas(xlim=[-3.0, 3.0], ylim=[-3.0, 3.0])

# === RUN ANIMATION ===
ani.run_animation()