import numpy as np
import matplotlib.pyplot as plt

# künstliche "Mikroskop-Oberfläche"
Z, X = 200, 200
x = np.linspace(0, 100, X)
z = np.linspace(0, 100, Z)
Xg, Zg = np.meshgrid(x, z)

# pseudo-heightmap (glatt + Struktur)
Yg = 2 * np.sin(Xg * 0.1) + 2 * np.cos(Zg * 0.1) + 0.5 * np.random.randn(*Xg.shape)

fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection="3d")

surf = ax.plot_surface(Xg, Zg, Yg, cmap="inferno", linewidth=0)

ax.set_xlabel("X (µm)")
ax.set_ylabel("Z (µm)")
ax.set_zlabel("Height (µm)")

fig.colorbar(surf, ax=ax, label="Height (µm)")

plt.show()
