#include "C:/Users/pwite/OneDrive/Dokumente/003_original/solver/solver.c"

void generated_eqs(float* q, float* dq, float* _dq, float* _ddq, float t, size_t N) {
    // Auto-generated Euler-Lagrange Equations using sympy.physics.mechanics
    // Constants have been collapsed into their values.
    _dq[0] = dq[0];
    _ddq[0] = -5.0*q[0];
    _dq[1] = dq[1];
    _ddq[1] = -5.0*q[1];
return;
}

/* Adapter that bridges the single-particle float array logic to Vector2D arrays */
void dfdx_wrapper(Vector2D* q, Vector2D* dq, Vector2D* _dq, Vector2D* _ddq, float t, size_t N) {
    for(size_t i=0; i<N; ++i) {
        float temp_q[2]    = {q[i].x, q[i].y};
        float temp_dq[2]   = {dq[i].x, dq[i].y};
        float temp__dq[2]  = {0.0f, 0.0f};
        float temp__ddq[2] = {0.0f, 0.0f};

        // N=2 internally since a single 2D particle has 2 degrees of freedom (x, y)
        generated_eqs(temp_q, temp_dq, temp__dq, temp__ddq, t, 2);

        _dq[i].x  = temp__dq[0];
        _dq[i].y  = temp__dq[1];
        _ddq[i].x = temp__ddq[0];
        _ddq[i].y = temp__ddq[1];
    }
}
