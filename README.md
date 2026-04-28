# 🦇 Eco-Ceguera

**Eco-Ceguera** es un juego de sigilo y destreza mental en 2D desarrollado en Python utilizando la librería Pygame. En este juego, el entorno está completamente a oscuras y el jugador depende exclusivamente de una mecánica de sonar para navegar, revelar el mapa y evadir enemigos. 

El proyecto destaca por una implementación estructurada de mecánicas de propagación de ondas y máquinas de estados simples para controlar el comportamiento de los enemigos, manteniendo un enfoque en la legibilidad y las buenas prácticas de desarrollo.

## 🎮 Mecánicas de Juego

* **Ceguera Total:** La pantalla permanece negra. Solo las ondas de sonido revelan las paredes, la salida y los enemigos de forma temporal.
* **Riesgo y Recompensa:** Emitir un pulso de sonar revela tu entorno inmediato, pero las ondas también alertan a los enemigos cercanos sobre tu posición.
* **Señuelos Tácticos:** Dispones de una cantidad limitada de señuelos para generar falsos ecos en otras áreas del mapa, distrayendo a las patrullas enemigas y abriendo rutas de escape.
* **Objetivo:** Encontrar y alcanzar la casilla dorada parpadeante (salida) sin ser atrapado por las entidades que patrullan el nivel.

## ⚙️ Controles

| Acción | Teclado / Ratón |
| :--- | :--- |
| **Movimiento** | `W` `A` `S` `D` o `Flechas` |
| **Emitir Sonar** | `Clic Izquierdo` (Te delata) |
| **Lanzar Señuelo** | `Clic Derecho` (Distrae a los enemigos) |
| **Reiniciar Nivel** | `R` |
| **Salir del Juego** | `ESC` |

## 🛠️ Instalación y Ejecución

Asegúrate de tener [Python 3.x](https://www.python.org/downloads/) instalado en tu sistema.

1. Clona este repositorio en tu máquina local:
   ```bash
   git clone [https://github.com/tu-usuario/eco-ceguera.git](https://github.com/tu-usuario/eco-ceguera.git)
   cd eco-ceguera
